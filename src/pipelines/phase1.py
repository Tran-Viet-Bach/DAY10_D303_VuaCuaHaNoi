from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings, load_settings, normalized_provider
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

FALLBACK_JUDGE_MARKER = "Fallback heuristic judge"


def _step(number: int, title: str) -> None:
    print(f"\n[{number}/7] {title}")


def _load_or_fetch_raw(settings: Settings) -> tuple[list[PaperRecord], str]:
    """Chi goi Crossref khi thuc su can.

    Baseline phai tai lap duoc: neu moi lan chay lai deu fetch nguon thi corpus
    doi theo, va so sanh baseline/corrupted/repaired mat cong bang. Dat
    `REFRESH_SOURCE=1` khi co y muon lay snapshot moi.
    """
    path = settings.paths.raw_records_json
    if path.exists() and not settings.refresh_source:
        records = load_raw_records(path)
        print(f"      dung snapshot san co: {path.name} ({len(records)} records) - KHONG goi API")
        return records, "reused_snapshot"

    reason = "refresh_source=1" if path.exists() else "chua co snapshot"
    print(f"      fetch Crossref ({reason})")
    return fetch_source_records(settings), "fetched"


def _load_or_build_test_set(settings: Settings, df: pd.DataFrame) -> tuple[list[dict[str, Any]], str]:
    """Test set duoc dong bang sau lan tao dau tien.

    Sinh lai test set tren du lieu da doi se lam hong phep so sanh: cau hoi va
    ground truth phai giu nguyen thi ba trang thai moi do duoc tren cung thuoc do.
    """
    path = settings.paths.eval_testset
    if path.exists() and not settings.refresh_test_set:
        test_set = read_json(path)
        print(f"      dung test set da dong bang: {path.name} ({len(test_set)} cau hoi)")
        return test_set, "frozen"

    reason = "refresh_test_set=1" if path.exists() else "chua co test set"
    test_set = build_test_set(df, path)
    print(f"      tao test set moi ({reason}): {len(test_set)} cau hoi")
    return test_set, "rebuilt"


def _check_test_set_against_index(
    test_set: list[dict[str, Any]], index: LocalEmbeddingIndex
) -> list[str]:
    """Tim ground_truth_doc_ids khong con trong index.

    O baseline day phai la danh sach rong. Neu khong rong thi test set va corpus
    da lech nhau, moi so lieu phia sau deu khong dang tin.
    """
    indexed = set(index.documents_by_paper_id)
    missing: list[str] = []
    for item in test_set:
        for doc_id in item["ground_truth_doc_ids"]:
            if str(doc_id).lower() not in indexed:
                missing.append(f"{item['id']}:{doc_id}")
    return missing


def _run_agent_demo(settings: Settings, index: LocalEmbeddingIndex) -> None:
    """Demo agent tren vai cau hoi. Loi o day khong duoc lam hong baseline."""
    from retrieval.agent import build_agent

    questions = [
        "Which indexed paper is about roof design compliance? Give its paper_id.",
        "What does the indexed corpus say about quantum error correction thresholds?",
    ]
    try:
        agent = build_agent(settings, index)
    except Exception as exc:
        print(f"      BO QUA agent demo: {type(exc).__name__}: {str(exc)[:120]}")
        return

    records: list[dict[str, Any]] = []
    for question in questions:
        try:
            result = agent.invoke({"messages": [{"role": "user", "content": question}]})
            messages = result.get("messages", [])
            tool_calls = [
                (call.get("name") if isinstance(call, dict) else getattr(call, "name", "?"))
                for message in messages
                for call in (getattr(message, "tool_calls", None) or [])
            ]
            tool_outputs = [
                str(getattr(message, "content", ""))
                for message in messages
                if type(message).__name__ == "ToolMessage"
            ]
            answer = str(getattr(messages[-1], "content", "")) if messages else ""
            grounded = sorted(
                {
                    pid
                    for output in tool_outputs
                    for pid in index.documents_by_paper_id
                    if pid in output.lower()
                }
            )
            print(f"      tools={tool_calls or 'KHONG'} | paper_id trong tool output={len(grounded)}")
            records.append(
                {
                    "question": question,
                    "tools_called": tool_calls,
                    "paper_ids_in_tool_output": grounded,
                    "answer": answer,
                }
            )
        except Exception as exc:
            print(f"      loi agent: {type(exc).__name__}: {str(exc)[:120]}")
            records.append({"question": question, "error": f"{type(exc).__name__}: {exc}"})

    if records:
        write_json(
            settings.paths.demo_answers,
            {
                "provider": normalized_provider(settings),
                "model": settings.model_name,
                "collection": index.collection_name,
                "cases": records,
            },
        )


def main() -> None:
    settings = load_settings()
    run_date = now_utc()

    print("=" * 78)
    print("BASELINE PIPELINE (phase 1)")
    print("=" * 78)
    print(
        f"  provider={normalized_provider(settings)}  model={settings.model_name}  "
        f"top_k={settings.top_k}  max_output_tokens={settings.max_output_tokens}"
    )

    # 1. Raw
    _step(1, "Raw records")
    records, source_mode = _load_or_fetch_raw(settings)

    # 2. Clean
    _step(2, "Cleaning")
    df = build_clean_dataframe(records, run_date)
    cleaning_log = df.attrs["cleaning_log"]
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    write_json(settings.paths.cleaning_log, cleaning_log)
    print(
        f"      raw {cleaning_log['input_records']} -> clean {cleaning_log['output_rows']} "
        f"(dropped {cleaning_log['dropped_total']}, deduped {cleaning_log['deduped_total']})"
    )
    for reason, count in cleaning_log["dropped_by_reason"].items():
        print(f"        - {count} x {reason}")

    # 3. Index
    _step(3, "Embedding index")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"      collection={index.collection_name}  documents={index.collection.count()}")

    # 4. Test set (frozen)
    _step(4, "Evaluation set")
    test_set, test_set_mode = _load_or_build_test_set(settings, df)
    missing_docs = _check_test_set_against_index(test_set, index)
    if missing_docs:
        print(
            f"      CANH BAO: {len(missing_docs)} ground_truth_doc_id khong co trong index: "
            f"{missing_docs[:5]}"
        )
    else:
        print("      moi ground_truth_doc_id deu co trong index")

    # 5. Evaluate
    _step(5, "Evaluation")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        print(f"      {key:20}: {metrics[key]}")

    # Judge co that su dung LLM khong? `_judge_answer` nuot exception va roi ve
    # heuristic token_f1 ma van tra ve so - phai noi ro neu dieu do xay ra.
    fallback_rows = [
        item["id"] for item in bundle.answers if FALLBACK_JUDGE_MARKER in item["judge"]["reasoning"]
    ]
    if fallback_rows:
        print(
            f"      CANH BAO: {len(fallback_rows)}/{len(bundle.answers)} judge dung FALLBACK "
            f"heuristic, khong phai LLM: {fallback_rows}"
        )
    else:
        print(f"      judge dung LLM that cho ca {len(bundle.answers)} cau")

    # 6. Quality + freshness
    _step(6, "Data quality & freshness")
    quality = run_data_quality_checks(df, settings, "baseline_quality")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(
        f"      quality  : {'PASS' if quality['success'] else 'FAIL'} "
        f"({quality['success_count']}/{len(quality['checks'])})"
    )
    for check in quality["checks"]:
        if not check["success"]:
            print(
                f"        FAIL {check['check']}: observed={check['observed']} "
                f"expected={check['expected']}"
            )
    print(
        f"      freshness: is_fresh={freshness['is_fresh']} latest={freshness['latest_published']} "
        f"stale={freshness['stale_rows']}/{freshness['total_rows']}"
    )

    # 7. Report
    _step(7, "Report")
    dropped_detail = ", ".join(f"{k}={v}" for k, v in cleaning_log["dropped_by_reason"].items())
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "source_mode": source_mode,
        "raw_records": cleaning_log["input_records"],
        "clean_rows": cleaning_log["output_rows"],
        "dropped_rows": cleaning_log["dropped_total"],
        "dropped_by_reason": dropped_detail or "(none)",
        "deduped_rows": cleaning_log["deduped_total"],
        "collection_name": index.collection_name,
        "indexed_documents": index.collection.count(),
        "embedding_model": settings.embedding_model,
        "test_set_mode": test_set_mode,
        "test_set_size": len(test_set),
        "llm_provider": normalized_provider(settings),
        "llm_model": settings.model_name,
        "top_k": settings.top_k,
        "judge_fallback_rows": len(fallback_rows),
        "run_date": run_date.isoformat(),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality,
        freshness=freshness,
    )
    print(f"      {settings.paths.baseline_report}")

    # Demo agent (khong bat buoc, loi khong lam hong baseline)
    print("\n[demo] Agent")
    _run_agent_demo(settings, index)

    print("\n" + "=" * 78)
    print("ARTIFACTS")
    print("=" * 78)
    for label, path in [
        ("raw response", settings.paths.raw_api_response),
        ("raw records", settings.paths.raw_records_json),
        ("clean csv", settings.paths.clean_csv),
        ("clean json", settings.paths.clean_json),
        ("cleaning log", settings.paths.cleaning_log),
        ("embeddings", settings.paths.embeddings_json),
        ("test set", settings.paths.eval_testset),
        ("metrics", settings.paths.baseline_metrics),
        ("answers", settings.paths.baseline_answers),
        ("quality", settings.paths.quality_dir / "baseline_quality.json"),
        ("freshness", settings.paths.freshness_report),
        ("report", settings.paths.baseline_report),
    ]:
        status = f"{path.stat().st_size:>8,} B" if path.exists() else "  MISSING"
        print(f"  {status}  {label:<14} {path.relative_to(settings.paths.project_dir)}")
