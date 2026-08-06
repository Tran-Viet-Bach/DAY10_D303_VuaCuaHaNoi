from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json

_MIN_SUMMARY_CHARS = 100
_MIN_ROW_COUNT = 1


def _check(name: str, dimension: str, threshold: str, actual: Any, passed: bool) -> dict[str, Any]:
    return {
        "name": name,
        "dimension": dimension,
        "threshold": threshold,
        "actual": actual,
        "status": "PASS" if passed else "FAIL",
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    row_count = len(df)
    checks: list[dict[str, Any]] = []

    checks.append(
        _check(
            "row_count",
            "Volume",
            f">= {_MIN_ROW_COUNT}",
            row_count,
            row_count >= _MIN_ROW_COUNT,
        )
    )

    if row_count == 0:
        paper_id_null = 0
        paper_id_unique = True
        title_null = 0
        short_summary = 0
        duplicate_ids = 0
    else:
        paper_id_null = int((df["paper_id"].astype(str).str.strip() == "").sum())
        paper_id_unique = bool(df["paper_id"].is_unique)
        duplicate_ids = int(row_count - df["paper_id"].nunique())
        title_null = int((df["title"].astype(str).str.strip() == "").sum())
        short_summary = int((df["summary"].astype(str).str.len() < _MIN_SUMMARY_CHARS).sum())

    checks.append(_check("paper_id_not_null", "Completeness", "0 missing", paper_id_null, paper_id_null == 0))
    checks.append(_check("paper_id_unique", "Uniqueness", "no duplicates", duplicate_ids, paper_id_unique))
    checks.append(_check("title_not_null", "Completeness", "0 missing", title_null, title_null == 0))
    checks.append(
        _check(
            "summary_min_length",
            "Validity",
            f">= {_MIN_SUMMARY_CHARS} chars",
            short_summary,
            short_summary == 0,
        )
    )

    if row_count == 0:
        stale_rows = 0
    else:
        stale_rows = int(
            ((df["age_days"] < 0) | (df["age_days"] > settings.freshness_threshold_days)).sum()
        )
    checks.append(
        _check(
            "freshness_age_days",
            "Freshness",
            f"<= {settings.freshness_threshold_days} days",
            stale_rows,
            stale_rows == 0,
        )
    )

    overall_status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    report = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "row_count": row_count,
        "checks": checks,
        "overall_status": overall_status,
    }

    output_path = settings.paths.quality_dir / f"{report_name}_quality.json"
    write_json(output_path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    if df is None or df.empty:
        payload = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": False,
        }
        write_json(report_path, payload)
        return payload

    published = df["published"].replace("", pd.NA).dropna()
    latest_published = published.max() if not published.empty else None
    oldest_published = published.min() if not published.empty else None

    stale_rows = int(
        ((df["age_days"] < 0) | (df["age_days"] > settings.freshness_threshold_days)).sum()
    )
    total_rows = len(df)

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": stale_rows == 0,
    }
    write_json(report_path, payload)
    return payload
