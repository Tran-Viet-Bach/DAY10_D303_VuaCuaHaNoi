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
