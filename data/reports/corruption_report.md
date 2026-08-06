# Corruption & Repair Comparison Report

Generated at: 2026-08-06T03:24:40.017991+00:00

## Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Δ Corruption | Δ Recovery |
| --- | --- | --- | --- | --- | --- |
| `retrieval_hit_rate` | 1.0000 | 0.8750 | 1.0000 | -0.1250 | 0.1250 |
| `mean_token_f1` | 1.0000 | 0.7674 | 1.0000 | -0.2326 | 0.2326 |
| `judge_accuracy` | 0.7500 | 0.6250 | 0.7500 | -0.1250 | 0.1250 |
| `mean_judge_score` | 4.7500 | 4.3750 | 4.7500 | -0.3750 | 0.3750 |

## Data Quality — Corrupted

Overall status: **FAIL**

| Check | Dimension | Threshold | Actual | Status |
| --- | --- | --- | --- | --- |
| row_count | Volume | >= 1 | 24 | PASS |
| paper_id_not_null | Completeness | 0 missing | 0 | PASS |
| paper_id_unique | Uniqueness | no duplicates | 1 | FAIL |
| title_not_null | Completeness | 0 missing | 0 | PASS |
| summary_min_length | Validity | >= 100 chars | 1 | FAIL |
| freshness_age_days | Freshness | <= 180 days | 1 | FAIL |

## Data Quality — Repaired

Overall status: **PASS**

| Check | Dimension | Threshold | Actual | Status |
| --- | --- | --- | --- | --- |
| row_count | Volume | >= 1 | 24 | PASS |
| paper_id_not_null | Completeness | 0 missing | 0 | PASS |
| paper_id_unique | Uniqueness | no duplicates | 0 | PASS |
| title_not_null | Completeness | 0 missing | 0 | PASS |
| summary_min_length | Validity | >= 100 chars | 0 | PASS |
| freshness_age_days | Freshness | <= 180 days | 0 | PASS |

## Freshness — Corrupted

- Stale rows: 1 / 24
- Is fresh: **False**

## Freshness — Repaired

- Stale rows: 0 / 24
- Is fresh: **True**
