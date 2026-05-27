# Harvest Year-By-Year Hardening Audit 2026

Read-only audit of normalized harvest truth against the current 2026 canonical hunt-code universe.

## Topline

- Current DATABASE hunt codes: 1449
- Harvest best rows: 5151
- Harvest long rows: 68657
- Current codes covered in at least one harvest year: 1242
- Current codes missing from all harvest years: 207
- Historical harvest codes not in current DATABASE: 182

## Year Coverage

| Reported hunt year | Best rows | Current codes covered | Current codes missing | Coverage | Metric warnings |
|---|---:|---:|---:|---:|---:|
| 2021 | 974 | 836 | 613 | 57.69% | 1008 |
| 2022 | 924 | 824 | 625 | 56.87% | 1320 |
| 2023 | 1078 | 1009 | 440 | 69.63% | 1250 |
| 2024 | 1048 | 1003 | 446 | 69.22% | 11931 |
| 2025 | 1127 | 1122 | 327 | 77.43% | 12 |

## Guardrails

- This audit does not change harvest truth rows, `DATABASE.csv`, website feeds, or draw predictions.
- Missing rows are repair targets, not proof that a hunt lacked harvest.
- Harvest `permits` fields remain report-context values and are not draw allotments.
