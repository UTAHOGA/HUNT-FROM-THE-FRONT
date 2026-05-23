# Database Publish Readiness Report

Generated UTC: 2026-05-23T10:14:59.597529+00:00
Publish ready: **YES**

## Blockers

- None

## Warnings

- Control-unit overlay unresolved warnings retained: Henry Mtns

## Source To Database

- Database rows: 1411
- Database unique hunt codes: 1411
- RAC hunt codes missing in database: 0
- RAC numeric mismatch rows: 0
- RAC significant differences > 5: 0

## New 2026 RAC Rows Explaining Stale Catalog Gap

- Stale 1,394-code catalog files are missing 17 new 2026 RAC hunt codes.
- 16 are new 2026 antlerless elk general-season hunt codes where 2025 permit columns were dashes and 2026 columns contain permits.
- 1 is the new 2026 doe pronghorn hunt `PD1039`.
- These rows account for 1,150 current-year permits (`1,034` resident / `116` nonresident).
- Detailed pullout: `processed_data/new_2026_rac_hunts_explain_1394_gap.md`.

## Database To Runtime

- Permit integrity blockers: 0
- Permit integrity mismatches after sync: 0
- Antlerless elk database differences: 0
- Antlerless elk runtime differences: 0

## Guardrails

- Null-probability violations: 0
- `ml_draw_predictions_v1` duplicate keys: 0
- `draw_reality_engine_predictive_v2` duplicate keys: 0
- Old internal draw-family label hits: 0
- Sensitive row failed checks: 0

