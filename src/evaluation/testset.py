from __future__ import annotations

import re
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

<<<<<<< HEAD
MIN_DOCUMENTS = 8
# So cau hoi moi loai. Tong 12 > muc toi thieu 5-10 cua de bai.
QUESTION_PLAN: list[tuple[str, int]] = [
    ("summary", 4),
    ("authors", 3),
    ("date", 3),
    ("categories", 2),
]


def _select_papers(df: pd.DataFrame, count: int) -> pd.DataFrame:
    """Chon paper trai deu tren truc thoi gian, khong lay mot cum lien nhau.

    Quan trong cho thi nghiem corruption: kich ban "drop latest records" chi lam
    metric giam neu test set thuc su co paper moi nhat. Lay `head(n)` se cho test
    set lech ve mot phia va che mat tac dong do.
    """
    total = len(df)
    if count >= total:
        return df.copy()
    step = (total - 1) / (count - 1) if count > 1 else 0
    positions = sorted({round(i * step) for i in range(count)})
    return df.iloc[positions].copy()


def _build_question(question_type: str, row: pd.Series) -> tuple[str, str]:
    """Sinh (question, ground_truth) khop dung nhanh xu ly cua `qa.py`.

    `_extract_answer` chon field tra ve dua tren tu khoa trong cau hoi, nen cau hoi
    va ground_truth phai duoc sinh cung mot cho - neu lech thi metric do sai lech
    cua chinh test set chu khong do chat luong retrieval.

    Dat title trong nhay don se kich hoat nhanh exact lookup cua `answer_question`;
    cau hoi loai summary co y KHONG dung nhay don de bat buoc di qua semantic search.
    """
    title = row["title"]

    if question_type == "authors":
        # "who authored" -> metadata["authors_joined"]
        return f"Who authored the paper titled '{title}'?", row["authors_joined"]

    if question_type == "date":
        # "when was" -> metadata["published"]
        return f"When was the paper titled '{title}' published?", row["published"]

    if question_type == "categories":
        # "what categories" -> metadata["categories_joined"]
        return (
            f"What categories are listed for the paper titled '{title}'?",
            row["categories_joined"],
        )

    # Mac dinh -> first_sentence(metadata["summary"]).
    # Khong co nhay don va khong chua tu khoa cua ba nhanh tren.
    return f"What problem does the paper titled {title} address?", first_sentence(row["summary"])


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set co dinh tu cleaned dataframe.

    Bo cau hoi nay duoc dong bang: baseline, corrupted va repaired deu phai duoc
    cham tren dung bo nay thi phep so sanh moi co nghia.
    """
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(
            f"Can it nhat {MIN_DOCUMENTS} document de tao test set, chi co {len(df)}."
        )

    required = ["paper_id", "title", "summary", "authors_joined", "categories_joined", "published"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Cleaned dataframe thieu cot: {missing}")

    # Title chua nhay don se pha regex r"'([^']+)'" cua exact lookup.
    usable = df[~df["title"].str.contains("'", regex=False)].reset_index(drop=True)
    if usable.empty:
        raise ValueError("Khong con paper nao co title dung duoc cho exact lookup.")

    total_questions = sum(count for _, count in QUESTION_PLAN)
    selected = _select_papers(usable, total_questions).reset_index(drop=True)

    test_set: list[dict[str, Any]] = []
    index = 0
    for question_type, count in QUESTION_PLAN:
        for _ in range(count):
            if index >= len(selected):
                break
            row = selected.iloc[index]
            index += 1

            question, ground_truth = _build_question(question_type, row)
            if not str(ground_truth).strip():
                # Khong tao cau hoi khong co dap an trong du lieu.
                continue

            test_set.append(
                {
                    "id": f"q{len(test_set) + 1}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": str(ground_truth),
                    "ground_truth_doc_ids": [row["paper_id"]],
                }
            )

    write_json(output_path, test_set)
    return test_set
=======
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
>>>>>>> 78ad189d2614d9fb9eebc8fa7bc650aa41113ada
