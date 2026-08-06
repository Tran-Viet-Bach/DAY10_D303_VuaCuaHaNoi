from __future__ import annotations

from typing import Any

from core.utils import now_utc, write_text


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _quality_table(quality: dict[str, Any]) -> str:
    checks = quality.get("checks", [])
    lines = ["| Check | Dimension | Threshold | Actual | Status |", "| --- | --- | --- | --- | --- |"]
    for check in checks:
        lines.append(
            f"| {check['name']} | {check['dimension']} | {check['threshold']} | "
            f"{check['actual']} | {check['status']} |"
        )
    return "\n".join(lines)


def _metrics_table(metrics: dict[str, Any]) -> str:
    keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    lines = ["| Metric | Value |", "| --- | --- |"]
    for key in keys:
        lines.append(f"| `{key}` | {_fmt(metrics.get(key, 'N/A'))} |")
    if "judge_backend" in metrics:
        lines.append(f"| judge_backend | {metrics['judge_backend']} |")
    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    lines = [
        "# Phase 1 — Baseline Pipeline Report",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "## Source",
        "",
        *[f"- **{key}**: {value}" for key, value in source_summary.items()],
        "",
        "## Evaluation Metrics",
        "",
        _metrics_table(metrics),
        "",
        f"Samples evaluated: {metrics.get('samples', 'N/A')}",
        "",
        "## Data Quality",
        "",
        f"Overall status: **{quality.get('overall_status', 'N/A')}**",
        "",
        _quality_table(quality),
        "",
        "## Freshness",
        "",
        f"- Latest published: {freshness.get('latest_published')}",
        f"- Oldest published: {freshness.get('oldest_published')}",
        f"- Stale rows: {freshness.get('stale_rows')} / {freshness.get('total_rows')}",
        f"- Is fresh: **{freshness.get('is_fresh')}**",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    metric_keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]

    comparison_lines = [
        "| Metric | Baseline | Corrupted | Repaired | Δ Corruption | Δ Recovery |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key in metric_keys:
        base = baseline_metrics.get(key)
        corrupt = corrupted_metrics.get(key)
        repaired = repaired_metrics.get(key)
        delta_corruption = corrupt - base if isinstance(base, (int, float)) and isinstance(corrupt, (int, float)) else "N/A"
        delta_recovery = repaired - corrupt if isinstance(repaired, (int, float)) and isinstance(corrupt, (int, float)) else "N/A"
        comparison_lines.append(
            f"| `{key}` | {_fmt(base)} | {_fmt(corrupt)} | {_fmt(repaired)} | "
            f"{_fmt(delta_corruption)} | {_fmt(delta_recovery)} |"
        )

    lines = [
        "# Corruption & Repair Comparison Report",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "## Metrics Comparison",
        "",
        *comparison_lines,
        "",
        "## Data Quality — Corrupted",
        "",
        f"Overall status: **{corrupted_quality.get('overall_status', 'N/A')}**",
        "",
        _quality_table(corrupted_quality),
        "",
        "## Data Quality — Repaired",
        "",
        f"Overall status: **{repaired_quality.get('overall_status', 'N/A')}**",
        "",
        _quality_table(repaired_quality),
        "",
        "## Freshness — Corrupted",
        "",
        f"- Stale rows: {corrupted_freshness.get('stale_rows')} / {corrupted_freshness.get('total_rows')}",
        f"- Is fresh: **{corrupted_freshness.get('is_fresh')}**",
        "",
        "## Freshness — Repaired",
        "",
        f"- Stale rows: {repaired_freshness.get('stale_rows')} / {repaired_freshness.get('total_rows')}",
        f"- Is fresh: **{repaired_freshness.get('is_fresh')}**",
        "",
    ]
    write_text(report_path, "\n".join(lines))
