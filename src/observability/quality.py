from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
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
    }
    write_json(report_path, payload)
    return payload
