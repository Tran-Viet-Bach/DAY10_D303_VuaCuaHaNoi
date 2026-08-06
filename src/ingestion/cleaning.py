from __future__ import annotations

from collections import Counter
from datetime import date, datetime
import html
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

# Nguong loai record. De o module level de audit va chinh duoc ma khong phai doc code.
MIN_SUMMARY_CHARS = 100
MIN_TITLE_CHARS = 10
# Abstract khong phai tieng Anh: MiniLM (all-MiniLM-L6-v2) xu ly rat kem, ma toan bo
# evaluation set la tieng Anh -> record nhu vay chi lam nhieu index.
MAX_NON_ASCII_RATIO = 0.30

# Crossref boc abstract trong <jats:title>Abstract</jats:title>; strip tag xong con lai
# chu "Abstract" o dau summary.
_ABSTRACT_PREFIX_PATTERN = re.compile(r"^abstract\b[\s:.\-]*", re.IGNORECASE)
_TAG_PATTERN = re.compile(r"<[^>]+>")

CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "summary_chars",
    "abs_url",
    "pdf_url",
    "text_for_embedding",
]


def _clean_text(value: str) -> str:
    """Phong thu: strip tag/entity mot lan nua phong khi raw snapshot con sot."""
    return normalize_whitespace(html.unescape(_TAG_PATTERN.sub(" ", str(value or ""))))


def _clean_summary(value: str) -> str:
    return _ABSTRACT_PREFIX_PATTERN.sub("", _clean_text(value)).strip()


def _non_ascii_ratio(value: str) -> float:
    if not value:
        return 0.0
    return sum(1 for char in value if ord(char) > 127) / len(value)


def _normalize_list(values: list[str]) -> list[str]:
    """Chuan hoa, bo rong, dedupe trong pham vi mot record (giu thu tu goc)."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        cleaned = _clean_text(value)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def _parse_date(value: str) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def build_text_for_embedding(title: str, authors_joined: str, summary: str) -> str:
    """Format bat buoc theo de bai: `Title: ... | Authors: ... | Summary: ...`.

    `categories` va `published` co y KHONG nam trong text duoc embed. Dieu do chap
    nhan duoc vi `qa.py::_extract_answer` doc thang tu Chroma metadata
    (`metadata["published"]`, `metadata["categories_joined"]`) chu khong doc tu
    content, nen cau tra loi van dung mien la retrieve trung dung document.
    """
    return f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    Moi record bi loai hoac bi dedupe deu duoc ghi lai kem ly do trong
    `df.attrs["cleaning_log"]` - khong bao gio lam mat record am tham.
    """
    run_day = run_date.date()

    rows: list[dict] = []
    dropped: list[dict[str, str]] = []
    deduped: list[dict[str, str]] = []
    future_published: list[str] = []
    seen_paper_ids: set[str] = set()

    def drop(record: PaperRecord, reason: str, detail: str) -> None:
        dropped.append(
            {
                "paper_id": record.paper_id or "(missing)",
                "title": _clean_text(record.title)[:80],
                "reason": reason,
                "detail": detail,
            }
        )

    for record in records:
        paper_id = str(record.paper_id or "").strip().lower()
        if not paper_id:
            drop(record, "missing_paper_id", "paper_id rong sau khi chuan hoa")
            continue

        title = _clean_text(record.title)
        if len(title) < MIN_TITLE_CHARS:
            drop(record, "title_too_short", f"{len(title)} < {MIN_TITLE_CHARS} ky tu")
            continue

        summary = _clean_summary(record.summary)
        if len(summary) < MIN_SUMMARY_CHARS:
            drop(record, "summary_too_short", f"{len(summary)} < {MIN_SUMMARY_CHARS} ky tu")
            continue

        ratio = _non_ascii_ratio(summary)
        if ratio > MAX_NON_ASCII_RATIO:
            drop(record, "non_english_summary", f"non-ascii {ratio:.0%} > {MAX_NON_ASCII_RATIO:.0%}")
            continue

        published_date = _parse_date(record.published)
        if published_date is None:
            drop(record, "unparsable_published", f"published={record.published!r}")
            continue

        # Dedupe theo stable ID. Giu ban gap dau tien vi Crossref tra ve theo do
        # lien quan giam dan.
        if paper_id in seen_paper_ids:
            deduped.append(
                {"paper_id": paper_id, "title": title[:80], "reason": "duplicate_paper_id"}
            )
            continue
        seen_paper_ids.add(paper_id)

        age_days = (run_day - published_date).days
        if age_days < 0:
            # Crossref cho phep `issued` o tuong lai (tap chi de ngay phat hanh sau).
            # Giu lai record nhung ghi nhan de quality check khong hieu nham.
            future_published.append(paper_id)

        authors = _normalize_list(record.authors)
        categories = _normalize_list(record.categories)
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        published = published_date.isoformat()

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "primary_category": categories[0] if categories else "",
                "published": published,
                "updated": _clean_text(record.updated),
                "age_days": age_days,
                "summary_chars": len(summary),
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
                "text_for_embedding": build_text_for_embedding(title, authors_joined, summary),
            }
        )

    df = pd.DataFrame(rows, columns=CLEAN_COLUMNS)
    if not df.empty:
        # Sort on dinh: moi lan chay cho cung thu tu -> so sanh 3 trang thai cong bang.
        df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    # Title trung nhung khac DOI la chuyen binh thuong (preprint vs ban published),
    # nen chi ghi nhan chu KHONG drop - drop se lam mat ban ghi hop le.
    duplicate_titles = (
        [title for title, count in Counter(df["title"].str.lower()).items() if count > 1]
        if not df.empty
        else []
    )

    df.attrs["cleaning_log"] = {
        "run_date": run_date.isoformat(),
        "input_records": len(records),
        "output_rows": int(len(df)),
        "dropped_total": len(dropped),
        "deduped_total": len(deduped),
        "dropped_by_reason": dict(Counter(item["reason"] for item in dropped)),
        "dropped_records": dropped,
        "deduped_records": deduped,
        "thresholds": {
            "min_summary_chars": MIN_SUMMARY_CHARS,
            "min_title_chars": MIN_TITLE_CHARS,
            "max_non_ascii_ratio": MAX_NON_ASCII_RATIO,
        },
        "anomalies": {
            "duplicate_titles": duplicate_titles,
            "future_published_ids": future_published,
            "rows_missing_pdf_url": int((df["pdf_url"] == "").sum()) if not df.empty else 0,
            "rows_missing_categories": (
                int((df["categories_joined"] == "").sum()) if not df.empty else 0
            ),
        },
    }

    return df
