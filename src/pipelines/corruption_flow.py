from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
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

    if not paths.baseline_metrics.exists() or not paths.clean_csv.exists():
        raise RuntimeError(
            "Baseline artifacts not found. Run `script/run_phase1.py` before the corruption flow."
        )

    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_df = pd.read_csv(paths.clean_csv, dtype=str, keep_default_na=False)
    baseline_df["age_days"] = baseline_df["age_days"].astype(int)

    test_set = read_json(paths.eval_testset)
    ground_truth_doc_ids = [item["ground_truth_doc_ids"][0] for item in test_set]
    judge_backend = _detect_judge_backend(settings)

    # --- Corrupt ---
    corrupted_df = corrupt_clean_dataframe(
        baseline_df, paths.corruption_log, ground_truth_doc_ids=ground_truth_doc_ids
    )
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings=settings, embeddings_output_path=paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )
    corrupted_metrics = dict(corrupted_bundle.summary)
    corrupted_metrics["judge_backend"] = judge_backend
    write_json(paths.corrupted_metrics, corrupted_metrics)

    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "corrupted_freshness_report.json"
    )

    # --- Repair: re-run cleaning from the untouched raw snapshot, never from corrupted/baseline copies ---
    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date=now_utc())
    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings=settings, embeddings_output_path=paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )
    repaired_metrics = dict(repaired_bundle.summary)
    repaired_metrics["judge_backend"] = judge_backend
    write_json(paths.repaired_metrics, repaired_metrics)

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "repaired_freshness_report.json"
    )

    baseline_ids = set(baseline_df["paper_id"])
    repaired_ids = set(repaired_df["paper_id"])
    lineage_match = baseline_ids == repaired_ids
    print(f"Lineage check (repaired paper_id set == baseline paper_id set): {lineage_match}")
    if not lineage_match:
        print(f"  missing from repaired: {baseline_ids - repaired_ids}")
        print(f"  unexpected in repaired: {repaired_ids - baseline_ids}")

    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )

    print(
        "Corruption flow complete. retrieval_hit_rate "
        f"baseline={baseline_metrics['retrieval_hit_rate']:.3f} "
        f"corrupted={corrupted_metrics['retrieval_hit_rate']:.3f} "
        f"repaired={repaired_metrics['retrieval_hit_rate']:.3f}"
    )
