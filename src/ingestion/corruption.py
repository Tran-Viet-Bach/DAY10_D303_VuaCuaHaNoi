from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import now_utc, write_json

_STALE_PUBLISHED = "2000-01-01"
_STALE_AGE_DAYS_SENTINEL = 9999
_TRUNCATE_TITLE_CHARS = 12
_NOISE_SUFFIX = " [INJECTED NOISE] Lorem ipsum dolor sit amet corrupted-content-8f3ac1."


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    return f"Title: {row['title']}\nAuthors: {row['authors_joined']}\nSummary: {row['summary']}"


def _row_index_for(df: pd.DataFrame, paper_id: str) -> int | None:
    matches = df.index[df["paper_id"] == paper_id]
    return matches[0] if len(matches) else None


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path,
    ground_truth_doc_ids: list[str] | None = None,
) -> pd.DataFrame:
    corrupted = df.copy().reset_index(drop=True)
    entries: list[dict[str, Any]] = []

    gt_pool = [pid for pid in dict.fromkeys(ground_truth_doc_ids or []) if pid in set(corrupted["paper_id"])]
    gt_set = set(ground_truth_doc_ids or [])
    non_gt_ids = [pid for pid in corrupted["paper_id"] if pid not in gt_set]

    def next_gt_target(fallback_id: str) -> str:
        return gt_pool.pop(0) if gt_pool else fallback_id

    def log(corruption_type: str, paper_id: str, param: str, before: Any, after: Any) -> None:
        entries.append(
            {
                "type": corruption_type,
                "paper_id": paper_id,
                "param": param,
                "before": before,
                "after": after,
                "in_ground_truth": paper_id in gt_set,
            }
        )

    # 1. Drop a latest record — prefers a ground-truth doc so retrieval_hit_rate is forced to change.
    latest_fallback = corrupted.sort_values("published", ascending=False).iloc[0]["paper_id"]
    drop_target = next_gt_target(latest_fallback)
    idx = _row_index_for(corrupted, drop_target)
    if idx is not None:
        title = corrupted.at[idx, "title"]
        log("drop_latest_record", drop_target, "row_removed", f"present (title='{title}')", "REMOVED")
        corrupted = corrupted[corrupted["paper_id"] != drop_target].reset_index(drop=True)

    # 2. Blank summary on another ground-truth doc.
    blank_target = next_gt_target(corrupted.iloc[0]["paper_id"])
    idx = _row_index_for(corrupted, blank_target)
    if idx is not None:
        before = corrupted.at[idx, "summary"]
        corrupted.at[idx, "summary"] = ""
        log("blank_summary", blank_target, "summary=''", before[:80], "")

    # 3. Inject noise into a non-ground-truth doc (general corpus noise, not targeted).
    noise_target = non_gt_ids[0] if non_gt_ids else corrupted.iloc[0]["paper_id"]
    idx = _row_index_for(corrupted, noise_target)
    if idx is not None:
        before = corrupted.at[idx, "summary"]
        corrupted.at[idx, "summary"] = before + _NOISE_SUFFIX
        log("add_noise", noise_target, "append_noise_text", before[:80], corrupted.at[idx, "summary"][:80])

    # 4. Truncate title on another ground-truth doc — breaks the exact-lookup path in qa.py.
    truncate_target = next_gt_target(corrupted.iloc[0]["paper_id"])
    idx = _row_index_for(corrupted, truncate_target)
    if idx is not None:
        before = corrupted.at[idx, "title"]
        corrupted.at[idx, "title"] = before[:_TRUNCATE_TITLE_CHARS]
        log(
            "truncate_title",
            truncate_target,
            f"keep_first_{_TRUNCATE_TITLE_CHARS}_chars",
            before,
            corrupted.at[idx, "title"],
        )

    # 5. Stale publication date on another ground-truth doc — breaks freshness + the date answer.
    stale_target = next_gt_target(corrupted.iloc[0]["paper_id"])
    idx = _row_index_for(corrupted, stale_target)
    if idx is not None:
        before = corrupted.at[idx, "published"]
        corrupted.at[idx, "published"] = _STALE_PUBLISHED
        corrupted.at[idx, "age_days"] = _STALE_AGE_DAYS_SENTINEL
        log("stale_date", stale_target, f"published={_STALE_PUBLISHED}", before, _STALE_PUBLISHED)

    # 6. Duplicate a non-ground-truth row — breaks the paper_id uniqueness quality check.
    dup_source = non_gt_ids[1] if len(non_gt_ids) > 1 else corrupted.iloc[0]["paper_id"]
    dup_rows = corrupted[corrupted["paper_id"] == dup_source]
    if not dup_rows.empty:
        corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
        log("duplicate_row", dup_source, "row_duplicated", "1 occurrence", "2 occurrences")

    for changed_id in {blank_target, truncate_target, noise_target}:
        for idx in corrupted.index[corrupted["paper_id"] == changed_id]:
            corrupted.at[idx, "text_for_embedding"] = _rebuild_text_for_embedding(corrupted.loc[idx])

    write_json(
        output_log_path,
        {
            "generated_at": now_utc().isoformat(),
            "original_row_count": len(df),
            "corrupted_row_count": len(corrupted),
            "entries": entries,
        },
    )
    return corrupted
