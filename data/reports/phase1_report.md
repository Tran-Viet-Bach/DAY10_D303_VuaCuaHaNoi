<<<<<<< HEAD
# Phase 1 — Baseline report

## Source

| Field | Value |
| --- | --- |
| `source_api` | Crossref REST API |
| `source_query` | agentic retrieval augmented generation large language model |
| `source_filter` | from-pub-date:2026-02-07,has-abstract:true |
| `source_mode` | reused_snapshot |
| `raw_records` | 24 |
| `clean_rows` | 23 |
| `dropped_rows` | 1 |
| `dropped_by_reason` | non_english_summary=1 |
| `deduped_rows` | 0 |
| `collection_name` | papers-baseline |
| `indexed_documents` | 23 |
| `embedding_model` | sentence-transformers/all-MiniLM-L6-v2 |
| `test_set_mode` | frozen |
| `test_set_size` | 12 |
| `llm_provider` | openai |
| `llm_model` | gpt-4.1-mini |
| `top_k` | 4 |
| `judge_fallback_rows` | 0 |
| `run_date` | 2026-08-06T03:54:14.555593+00:00 |

## Evaluation metrics

| Metric | Value |
| --- | --- |
| `samples` | 12 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |

## Ragas

| Field | Value |
| --- | --- |
| `skipped` | Set RUN_RAGAS=1 to enable the slower Ragas pass. |

## Data quality

- Dataset: `baseline_quality`
- Rows: 23
- Passed: 9 / failed: 0
- Overall: **PASS**

| Check | Result | Observed | Expected |
| --- | --- | --- | --- |
| `row_count_positive` | PASS | 23 | > 0 |
| `paper_id_not_null` | PASS | 0 | 0 rong/null |
| `paper_id_unique` | PASS | 0 | 0 trung |
| `title_not_null` | PASS | 0 | 0 rong |
| `summary_not_null` | PASS | 0 | 0 rong |
| `summary_min_length` | PASS | 0 | 0 row < 100 ky tu |
| `text_for_embedding_not_empty` | PASS | 0 | 0 rong |
| `no_duplicate_titles` | PASS | 0 | 0 trung |
| `freshness_within_threshold` | PASS | 0 | 0 row > 180 ngay |

## Freshness

| Field | Value |
| --- | --- |
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2026-02-12 |
| `stale_rows` | 0 |
| `total_rows` | 23 |
| `is_fresh` | yes |
| `threshold_days` | 180 |
| `newest_age_days` | 5 |
| `oldest_age_days` | 175 |
| `stale_ratio` | 0.0000 |
| `stale_paper_ids` | (none) |
=======
# Phase 1 — Baseline Pipeline Report

Generated at: 2026-08-06T03:15:32.020761+00:00

## Source

- **source_api**: Crossref REST API
- **source_query**: agentic retrieval augmented generation large language model
- **source_filter**: from-pub-date:2026-02-07,has-abstract:true
- **max_results**: 24
- **raw_records**: 24
- **clean_records**: 24
- **test_set_size**: 8

## Evaluation Metrics

| Metric | Value |
| --- | --- |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 0.7500 |
| `mean_judge_score` | 4.7500 |
| judge_backend | ollama |

Samples evaluated: 8

## Data Quality

Overall status: **PASS**

| Check | Dimension | Threshold | Actual | Status |
| --- | --- | --- | --- | --- |
| row_count | Volume | >= 1 | 24 | PASS |
| paper_id_not_null | Completeness | 0 missing | 0 | PASS |
| paper_id_unique | Uniqueness | no duplicates | 0 | PASS |
| title_not_null | Completeness | 0 missing | 0 | PASS |
| summary_min_length | Validity | >= 100 chars | 0 | PASS |
| freshness_age_days | Freshness | <= 180 days | 0 | PASS |

## Freshness

- Latest published: 2026-08-01
- Oldest published: 2026-02-12
- Stale rows: 0 / 24
- Is fresh: **True**
>>>>>>> 78ad189d2614d9fb9eebc8fa7bc650aa41113ada
