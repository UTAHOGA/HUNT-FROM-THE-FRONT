# Hunt Master Canonical 2026 Built Permit Deep Dive

Read-only audit comparing the target file against DATABASE, direct RAC CSV evidence, and current-year total-scan evidence.

## Summary

- Target rows: `1289`
- Target unique hunt codes: `1289`
- DATABASE rows: `1411`
- Target codes missing DATABASE: `1`
- DATABASE codes missing target: `123`
- Direct RAC hunt codes: `519`
- Total-scan high-confidence hunt codes: `855`
- High-confidence rows: `318`
- Review-required rows: `492`
- Target 2026 mismatch rows: `461`
- Target 2025 mismatch rows: `504`
- Large 2025-to-2026 change review rows: `42`

## Guardrail

This audit is evidence only. It does not promote 2025 permit values into 2026 available allotment. Promotion still requires reviewed source-date context. Populated numeric permit cells in canonical DATABASE.csv are treated as direct Utah DWR Hunt Planner truth and must not be overwritten by comparison files, inferred values, draw reports, RAC files, or audit outputs.

## Status Counts

### target_2025_vs_database_2025

- `BOTH_BLANK`: `327`
- `LEFT_ONLY`: `28`
- `MATCH`: `438`
- `MISMATCH`: `158`
- `RIGHT_ONLY`: `318`
- `TOTAL_MATCH_SPLIT_DIFFERS`: `20`

### target_2025_vs_database_2025_draw

- `BOTH_BLANK`: `550`
- `LEFT_ONLY`: `167`
- `MATCH`: `386`
- `MISMATCH`: `91`
- `RIGHT_ONLY`: `95`

### target_2026_vs_database_2026

- `BOTH_BLANK`: `140`
- `LEFT_ONLY`: `5`
- `LEFT_ZERO_RIGHT_BLANK`: `1`
- `MATCH`: `687`
- `MISMATCH`: `292`
- `RIGHT_ONLY`: `163`
- `TOTAL_MATCH_SPLIT_DIFFERS`: `1`

### target_2026_vs_database_allotment

- `BOTH_BLANK`: `297`
- `LEFT_ONLY`: `197`
- `LEFT_ZERO_RIGHT_BLANK`: `281`
- `MATCH`: `505`
- `MISMATCH`: `3`
- `RIGHT_ONLY`: `6`

### target_2026_vs_direct_rac

- `BOTH_BLANK`: `303`
- `LEFT_ONLY`: `203`
- `LEFT_ZERO_RIGHT_BLANK`: `281`
- `MATCH`: `499`
- `MISMATCH`: `3`

### target_2026_vs_totalscan

- `BOTH_BLANK`: `151`
- `LEFT_ONLY`: `283`
- `MATCH`: `234`
- `MISMATCH`: `469`
- `RIGHT_ONLY`: `152`

### change_review

- `INSUFFICIENT_DATA`: `645`
- `LARGE_CHANGE_REVIEW`: `42`
- `MODERATE_CHANGE_ABS_GT_5_PCT_25_OR_LESS`: `36`
- `NO_CHANGE`: `271`
- `SMALL_CHANGE_ABS_5_OR_LESS`: `295`

### evidence_confidence

- `HIGH`: `318`
- `LOW_2025_MATCH_ONLY`: `109`
- `MEDIUM_2026_MATCHES_DATABASE`: `370`
- `REVIEW_REQUIRED`: `492`
