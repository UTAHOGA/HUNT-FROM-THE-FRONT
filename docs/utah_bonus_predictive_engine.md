# Utah Bonus Predictive Engine

This engine covers Utah `OIL`, `LE`, and `PLE` hunts and uses bonus-point logic for all three. `PLE` is treated as a premium limited-entry subclass, not a separate math system.

`MAX POOL` is descriptive only. Display odds come from modeled probability fields, not from status text. The live Hunt Research precedence is:

1. `p_draw_pct`
2. `p_draw` converted to percent
3. `p_bonus_pool_pct / p_random_pool_pct`
4. legacy fallback odds fields
5. `Not available`

## Core rules

- One permit is random-only: `1 permit -> 0 max-point / 1 random`
- Split examples:
  - `0 -> 0 / 0`
  - `1 -> 0 / 1`
  - `2 -> 1 / 1`
  - `3 -> 2 / 1`
  - `7 -> 4 / 3`
  - `9 -> 5 / 4`
  - `15 -> 8 / 7`

## EB3024 regression

`EB3024` is the permanent regression fixture that proves the Utah reserved/random split and cohort carry-forward behavior.

- 2024 Resident:
  - public `7`
  - bonus `4`
  - regular `3`
  - `29` points bonus pool `1.000`
  - `28` points bonus pool `0.333333`
  - unsuccessful `28`-point cohort `6`
- 2025 Resident:
  - public `9`
  - bonus `5`
  - regular `4`
  - `30` points bonus pool `1.000`
  - `29` points bonus pool `0.800`
  - retained `5 / 6 = 0.833333`
- 2024/2025 Nonresident:
  - public `1`
  - bonus `0`
  - regular `1`
  - random-only lane

## Forecasting model

The engine uses cohort carry-forward, not a blind average. Unsuccessful applicants roll forward one point into the next year, and multi-year history is used to calibrate retention, switch-in pressure, quota behavior, and backtest error.

The current production forecast year is `2026`, using source years `2021-2025`.

`2027` is intentionally not surfaced as an active forecast year in this repo right now. As of May 20, 2026, Utah's 2026 big game draw results had not yet been released, so a `2027` forecast would not have the required 2026 actual draw results as a source year.

## Artifacts

- `processed_data/ml_draw_predictions_v1.csv`
- `processed_data/ml_draw_predictions_v1_report.json`
- `processed_data/backtest_utah_bonus_draw.csv`
- `processed_data/backtest_utah_bonus_draw_report.json`
- `processed_data/draw_reality_engine_predictive_v2.csv`
- `processed_data/draw_reality_engine_v2.csv`
- `processed_data/predictive_coverage_report.json`
- `processed_data/predictive_coverage_report.csv`
- `processed_data/utah_bonus_predictive_manifest.json`

## CLI

```bash
python -m engine.utah_bonus_predictive.materialize \
  --output-dir processed_data \
  --forecast-year 2026 \
  --history-years 2021,2022,2023,2024,2025
```

Repeatable local regeneration without rebuilding upstream drafts:

```bash
python -m engine.utah_bonus_predictive.materialize \
  --output-dir processed_data \
  --forecast-year 2026 \
  --history-years 2021,2022,2023,2024,2025 \
  --skip-upstream
```

## Runtime modes

- Observed mode loads `draw_reality_engine_v2.csv`
- Predictive mode loads `draw_reality_engine_predictive_v2.csv`
- Config flag: `USE_PREDICTIVE_DRAW_ENGINE=true`
