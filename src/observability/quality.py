from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
<<<<<<< HEAD
from core.utils import write_json

# Nguong do dai summary cho quality gate. Doc lap voi nguong cua cleaning: cleaning
# quyet dinh giu hay bo record luc ingest, con day la tin hieu canh bao tren dataset
# da clean (corruption blank summary ma khong di qua cleaning).
MIN_SUMMARY_CHARS = 100


def _check(name: str, success: bool, observed: Any, expected: str) -> dict[str, Any]:
    return {"check": name, "success": bool(success), "observed": observed, "expected": expected}


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay bo data quality checks tren mot dataset da clean.

    Moi ket qua duoc tinh tu chinh dataframe, khong hard-code pass: dataset bi
    corrupt phai lam check that bai thi bao cao moi co gia tri lam bang chung.
    """
    total_rows = int(len(df))
    checks: list[dict[str, Any]] = [_check("row_count_positive", total_rows > 0, total_rows, "> 0")]

    if total_rows == 0:
        payload = {
            "report_name": report_name,
            "total_rows": 0,
            "checks": checks,
            "success_count": sum(1 for check in checks if check["success"]),
            "failed_count": sum(1 for check in checks if not check["success"]),
            "success": all(check["success"] for check in checks),
        }
        write_json(settings.paths.quality_dir / f"{report_name}.json", payload)
        return payload

    paper_id = df["paper_id"].fillna("").astype(str)
    missing_paper_id = int((paper_id.str.strip() == "").sum())
    checks.append(_check("paper_id_not_null", missing_paper_id == 0, missing_paper_id, "0 rong/null"))

    duplicate_ids = int(total_rows - paper_id.nunique())
    checks.append(_check("paper_id_unique", duplicate_ids == 0, duplicate_ids, "0 trung"))

    missing_title = int((df["title"].fillna("").astype(str).str.strip() == "").sum())
    checks.append(_check("title_not_null", missing_title == 0, missing_title, "0 rong"))

    summary = df["summary"].fillna("").astype(str)
    missing_summary = int((summary.str.strip() == "").sum())
    checks.append(_check("summary_not_null", missing_summary == 0, missing_summary, "0 rong"))

    short_summary = int((summary.str.len() < MIN_SUMMARY_CHARS).sum())
    checks.append(
        _check(
            "summary_min_length",
            short_summary == 0,
            short_summary,
            f"0 row < {MIN_SUMMARY_CHARS} ky tu",
        )
    )

    empty_embedding_text = int(
        (df["text_for_embedding"].fillna("").astype(str).str.strip() == "").sum()
    )
    checks.append(
        _check(
            "text_for_embedding_not_empty", empty_embedding_text == 0, empty_embedding_text, "0 rong"
        )
    )

    duplicate_titles = int(total_rows - df["title"].fillna("").astype(str).str.lower().nunique())
    checks.append(_check("no_duplicate_titles", duplicate_titles == 0, duplicate_titles, "0 trung"))

    ages = pd.to_numeric(df["age_days"], errors="coerce")
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    checks.append(
        _check(
            "freshness_within_threshold",
            stale_rows == 0,
            stale_rows,
            f"0 row > {settings.freshness_threshold_days} ngay",
        )
    )

    payload = {
        "report_name": report_name,
        "total_rows": total_rows,
        "checks": checks,
        "success_count": sum(1 for check in checks if check["success"]),
        "failed_count": sum(1 for check in checks if not check["success"]),
        "success": all(check["success"] for check in checks),
    }
    write_json(settings.paths.quality_dir / f"{report_name}.json", payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report tu `published` va `age_days`.

    `is_fresh` bam vao tuoi cua document MOI NHAT chu khong phai trung binh: hai
    kich ban corruption ("xoa latest records" va "lam stale publication date") deu
    day latest_published lui lai, nen tin hieu nay se doi khi du lieu bi hong.
    """
    total_rows = int(len(df))
    threshold = settings.freshness_threshold_days

    if total_rows == 0:
        payload = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": False,
            "threshold_days": threshold,
            "newest_age_days": None,
            "oldest_age_days": None,
            "stale_ratio": 0.0,
            "stale_paper_ids": [],
        }
        write_json(report_path, payload)
        return payload

    published = df["published"].fillna("").astype(str)
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    has_age = bool(ages.notna().any())
    newest_age = int(ages.min()) if has_age else None
    stale_mask = ages > threshold
    stale_rows = int(stale_mask.sum())

    payload = {
        "latest_published": published.max(),
        "oldest_published": published.min(),
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": newest_age is not None and newest_age <= threshold,
        "threshold_days": threshold,
        "newest_age_days": newest_age,
        "oldest_age_days": int(ages.max()) if has_age else None,
        "stale_ratio": round(stale_rows / total_rows, 4),
        "stale_paper_ids": df.loc[stale_mask.fillna(False), "paper_id"].astype(str).tolist(),
=======
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
>>>>>>> 78ad189d2614d9fb9eebc8fa7bc650aa41113ada
    }
    write_json(report_path, payload)
    return payload
