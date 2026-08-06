from __future__ import annotations

from typing import Any

<<<<<<< HEAD
from core.utils import write_text


def _format_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "(none)"
    return str(value)


def _kv_table(title: str, payload: dict[str, Any], skip: tuple[str, ...] = ()) -> list[str]:
    lines = [f"## {title}", "", "| Field | Value |", "| --- | --- |"]
    for key, value in payload.items():
        if key in skip:
            continue
        lines.append(f"| `{key}` | {_format_value(value)} |")
    lines.append("")
    return lines


def _quality_table(quality: dict[str, Any]) -> list[str]:
    lines = [
        "## Data quality",
        "",
        f"- Dataset: `{quality.get('report_name', 'n/a')}`",
        f"- Rows: {_format_value(quality.get('total_rows'))}",
        f"- Passed: {_format_value(quality.get('success_count'))} / "
        f"failed: {_format_value(quality.get('failed_count'))}",
        f"- Overall: **{'PASS' if quality.get('success') else 'FAIL'}**",
        "",
        "| Check | Result | Observed | Expected |",
        "| --- | --- | --- | --- |",
    ]
    for check in quality.get("checks", []):
        status = "PASS" if check.get("success") else "**FAIL**"
        lines.append(
            f"| `{check.get('check')}` | {status} | {_format_value(check.get('observed'))} "
            f"| {_format_value(check.get('expected'))} |"
        )
    lines.append("")
    return lines
=======
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
>>>>>>> 78ad189d2614d9fb9eebc8fa7bc650aa41113ada


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
<<<<<<< HEAD
    """Viet markdown report cho baseline phase.

    Moi so lieu deu lay tu payload truyen vao (metrics/quality/freshness that),
    khong co gia tri nao duoc viet cung trong template.
    """
    lines: list[str] = ["# Phase 1 — Baseline report", ""]

    lines += _kv_table("Source", source_summary)

    lines += ["## Evaluation metrics", "", "| Metric | Value |", "| --- | --- |"]
    for key, value in metrics.items():
        if key == "ragas":
            continue
        lines.append(f"| `{key}` | {_format_value(value)} |")
    lines.append("")

    ragas = metrics.get("ragas")
    if isinstance(ragas, dict):
        lines += _kv_table("Ragas", ragas)

    lines += _quality_table(quality)
    lines += _kv_table("Freshness", freshness)

    write_text(report_path, "\n".join(lines).rstrip() + "\n")
=======
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
>>>>>>> 78ad189d2614d9fb9eebc8fa7bc650aa41113ada


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
