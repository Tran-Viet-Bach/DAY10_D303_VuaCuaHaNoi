from __future__ import annotations

from datetime import datetime
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MIN_SUMMARY_CHARS = 100


def _strip_html(text: str) -> str:
    return normalize_whitespace(_HTML_TAG_RE.sub(" ", text or ""))


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    rows = []
    for record in records:
        title = normalize_whitespace(record.title)
        summary = _strip_html(record.summary)
        if not title or len(summary) < _MIN_SUMMARY_CHARS:
            continue

        authors_joined = compact_join(record.authors)
        categories_joined = compact_join(record.categories)

        published_ts = pd.to_datetime(record.published, errors="coerce")
        published = published_ts.date().isoformat() if pd.notna(published_ts) else ""
        if pd.notna(published_ts):
            age_days = (run_date.date() - published_ts.date()).days
        else:
            age_days = -1

        text_for_embedding = (
            f"Title: {title}\nAuthors: {authors_joined}\nSummary: {summary}"
        )

        rows.append(
            {
                "paper_id": record.paper_id,
                "title": title,
                "summary": summary,
                "published": published,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
                "abs_url": record.abs_url or "",
                "pdf_url": record.pdf_url or "",
            }
        )

    columns = [
        "paper_id",
        "title",
        "summary",
        "published",
        "authors_joined",
        "categories_joined",
        "age_days",
        "text_for_embedding",
        "abs_url",
        "pdf_url",
    ]
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return df

    df = df.drop_duplicates(subset="paper_id", keep="first")

    string_cols = [c for c in columns if c != "age_days"]
    for col in string_cols:
        df[col] = df[col].fillna("").astype(str)
    df["age_days"] = df["age_days"].fillna(-1).astype(int)

    df = df.sort_values("published", ascending=False, kind="stable").reset_index(drop=True)
    return df
