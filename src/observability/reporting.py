from __future__ import annotations

from typing import Any

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


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
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
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
