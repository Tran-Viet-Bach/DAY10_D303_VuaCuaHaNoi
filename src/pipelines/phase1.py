from __future__ import annotations

from datetime import datetime, UTC

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def _detect_judge_backend(settings) -> str:
    try:
        from retrieval.llm import build_llm

        build_llm(settings=settings, temperature=0.0)
        return settings.llm_provider
    except Exception:
        return "heuristic"


def main() -> None:
    settings = load_settings()
    paths = settings.paths

    # 1. Load or fetch raw records (fetch only when explicitly requested or no cache exists).
    if settings.refresh_source or not paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(paths.raw_records_json)

    # 2. Clean data.
    run_date = datetime.now(UTC)
    df = build_clean_dataframe(records, run_date=run_date)
    write_csv(df, paths.clean_csv)
    write_json(paths.clean_json, df.to_dict(orient="records"))

    # 3. Build baseline Chroma index.
    index = LocalEmbeddingIndex.build(df, settings=settings, embeddings_output_path=paths.embeddings_json)

    # 4. Create or load the frozen evaluation set.
    if settings.refresh_test_set or not paths.eval_testset.exists():
        build_test_set(df, paths.eval_testset)
    test_set = read_json(paths.eval_testset)

    # 5. Evaluate.
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    metrics = dict(bundle.summary)
    metrics["judge_backend"] = _detect_judge_backend(settings)
    write_json(paths.baseline_metrics, metrics)

    # 6. Data quality checks and freshness report.
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)

    # 7. Markdown report.
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        "raw_records": len(records),
        "clean_records": len(df),
        "test_set_size": len(test_set),
    }
    generate_phase1_report(paths.baseline_report, source_summary, metrics, quality, freshness)

    # 8. Demo the agent on a few sample questions (Mục 5 evidence).
    demo_answers = []
    try:
        agent = build_agent(settings, index)
        for item in test_set[:3]:
            answer = run_agent_question(agent, item["question"])
            demo_answers.append({"question": item["question"], "answer": answer})
    except Exception as exc:  # pragma: no cover
        demo_answers.append({"error": f"Agent demo failed: {exc}"})
    write_json(paths.demo_answers, demo_answers)

    print(f"Baseline pipeline complete. retrieval_hit_rate={metrics['retrieval_hit_rate']:.3f} "
          f"mean_token_f1={metrics['mean_token_f1']:.3f} judge_backend={metrics['judge_backend']}")
