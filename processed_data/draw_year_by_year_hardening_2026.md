# Draw Year-By-Year Hardening Audit 2026

Read-only audit of normalized draw-results truth against the current 2026 canonical hunt-code universe.

## Topline

- Current DATABASE hunt codes: 1449
- Draw long rows: 176753
- Unique draw hunt codes across all years: 1616
- Current codes covered in at least one draw year: 1446
- Current codes missing from all draw years: 3
- Expected trend: unique draw hunt-code count should generally increase slightly year over year, or any drop should be explained by source coverage, discontinued codes, split/renamed hunt codes, or true season structure changes.

## Year Coverage

| Draw year | Native unique draw codes | Draw rows |
|---|---:|---:|
| 2021 | 550 | 27519 |
| 2022 | 1024 | 18688 |
| 2023 | 1010 | 17128 |
| 2024 | 580 | 37128 |
| 2025 | 1053 | 75194 |
| 2026 | 548 | 1096 |

## Current Reference Alignment

The 2026 `DATABASE.csv` comparison is only for crosswalk/alignment work. It is not a completeness score for older draw years.

| Draw year | Current 2026 codes cross-referenced | Current 2026 codes not cross-referenced |
|---|---:|---:|
| 2021 | 490 | 959 |
| 2022 | 867 | 582 |
| 2023 | 883 | 566 |
| 2024 | 580 | 869 |
| 2025 | 1052 | 397 |
| 2026 | 548 | 901 |

## Data-Land Rule

- Draw odds/results stay in `data_truth/draw_results_truth` until a later feature-combine step.
- Harvest metrics stay in `data_truth/harvest_results_truth` until a later feature-combine step.
- Prediction features should combine these only after each domain has year-by-year coverage and source lineage.
