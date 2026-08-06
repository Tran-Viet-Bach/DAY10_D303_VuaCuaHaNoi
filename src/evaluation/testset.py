from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

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
