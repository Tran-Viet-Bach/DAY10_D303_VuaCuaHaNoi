from __future__ import annotations

import re
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

_MIN_CANDIDATES = 4
_MIN_QUESTIONS = 5
_MAX_PER_TYPE = 2
_ASCII_TITLE_RE = re.compile(r"^[\x20-\x7E]+$")


def _select_candidates(df: pd.DataFrame) -> pd.DataFrame:
    is_ascii = df["title"].str.match(_ASCII_TITLE_RE)
    has_no_quote = ~df["title"].str.contains("'", regex=False)
    return df[is_ascii & has_no_quote].reset_index(drop=True)


def _pick_rows(candidates: pd.DataFrame, used_ids: set[str], predicate, count: int) -> list[pd.Series]:
    picked: list[pd.Series] = []
    for _, row in candidates.iterrows():
        if row["paper_id"] in used_ids:
            continue
        if not predicate(row):
            continue
        picked.append(row)
        used_ids.add(row["paper_id"])
        if len(picked) >= count:
            break
    return picked


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if df is None or df.empty:
        raise ValueError("Cannot build a test set from an empty dataframe.")

    candidates = _select_candidates(df)
    if len(candidates) < _MIN_CANDIDATES:
        raise ValueError(
            "Not enough ASCII titles without apostrophes to build a reliable frozen test set "
            f"(found {len(candidates)}, need at least {_MIN_CANDIDATES})."
        )

    used_ids: set[str] = set()
    summary_rows = _pick_rows(candidates, used_ids, lambda r: True, _MAX_PER_TYPE)
    author_rows = _pick_rows(candidates, used_ids, lambda r: bool(r["authors_joined"]), _MAX_PER_TYPE)
    date_rows = _pick_rows(candidates, used_ids, lambda r: r["age_days"] != -1 and bool(r["published"]), _MAX_PER_TYPE)
    category_rows = _pick_rows(candidates, used_ids, lambda r: bool(r["categories_joined"]), _MAX_PER_TYPE)

    items: list[dict[str, Any]] = []
    counter = 1

    for row in summary_rows:
        items.append(
            {
                "id": f"q{counter}",
                "question_type": "summary",
                "question": f"Can you summarize the paper titled '{row['title']}'?",
                "ground_truth": first_sentence(row["summary"]),
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )
        counter += 1

    for row in author_rows:
        items.append(
            {
                "id": f"q{counter}",
                "question_type": "authors",
                "question": f"Who authored the paper titled '{row['title']}'?",
                "ground_truth": row["authors_joined"],
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )
        counter += 1

    for row in date_rows:
        items.append(
            {
                "id": f"q{counter}",
                "question_type": "date",
                "question": f"When was the paper titled '{row['title']}' published?",
                "ground_truth": row["published"],
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )
        counter += 1

    for row in category_rows:
        items.append(
            {
                "id": f"q{counter}",
                "question_type": "categories",
                "question": f"What categories does the paper titled '{row['title']}' belong to?",
                "ground_truth": row["categories_joined"],
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )
        counter += 1

    if len(items) < _MIN_QUESTIONS:
        raise ValueError(
            f"Only generated {len(items)} test questions; need at least {_MIN_QUESTIONS}. "
            "Not enough candidate rows with authors/categories/published metadata."
        )

    write_json(output_path, items)
    return items
