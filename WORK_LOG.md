# WORK LOG


## Step 1B - Raw Inventory Audit
- Timestamp (UTC): 2026-05-10T12:43:23.701298Z
- Total files audited: 1286
- Promoted quality sources: 253
- Promoted draw sources: 204
- Held/review sources: 829
- Biggest risks found:
  - High duplicate pressure: 296 files held as duplicates.
  - Unreadable PDFs: 13 files require source replacement or repair.
  - Review required: 489 files have unknown/conflicting metadata.
  - Missing year inference: 27 files need year assignment.
- Outputs:
  - data_model/quality/raw_pdf_inventory_audit.csv
  - data_model/quality/raw_pdf_inventory_audit_report.json

## Step 1C - Promoted Source Manifests
- Timestamp (UTC): 2026-05-10T13:16:50.588074+00:00
- Input: data_model/quality/raw_pdf_inventory_audit.csv
- Promoted quality sources: 253
- Promoted draw sources: 204
- Validation passed: True
- Promotion blockers: 0
- Outputs:
  - data_model/quality/promoted_quality_sources.csv
  - data_model/quality/promoted_draw_sources.csv
  - data_model/quality/promoted_source_summary.json

## Step 1D - Promoted Source Year Map
- Timestamp (UTC): 2026-05-10T13:34:21.393303+00:00
- Inputs:
  - data_model/quality/promoted_quality_sources.csv
  - data_model/quality/promoted_draw_sources.csv
  - data_model/quality/raw_pdf_inventory_audit.csv
- Promoted quality rows mapped: 253
- Promoted draw rows mapped: 204
- Total promoted rows in year map: 457
- Year conflicts (folder year vs reported hunt year): 222
- Year unknown rows: 0
- Validation passed: True
- Outputs:
  - data_model/quality/promoted_source_year_map.csv
  - data_model/quality/promoted_source_year_map_report.json

## Reference Baseline Audit - DATABASE.csv
- Timestamp (UTC): 2026-05-10T14:06:52.319022+00:00
- Source:
  - pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv
- Classification:
  - reference_role: canonical_2026_database_reference
  - derived_or_source: source_reference
  - usable_for_hunt_code_validation: YES
  - usable_for_2026_permit_reference: YES
  - usable_for_harvest_truth: NO
  - usable_for_draw_truth: NO
- Validation counts:
  - rows: 1395
  - unique hunt codes: 1394
  - duplicate hunt codes: 0
  - malformed/missing hunt_code rows: 1 (flagged/rejected for reference joins)
  - missing permits_2026_total rows (allowed): 321
  - total present with split missing (allowed): 194
  - res+nr vs total conflicts (blockers): 0
- Outputs:
  - data_model/quality/reference_baseline_audit.csv
  - data_model/quality/reference_baseline_audit_report.json

## Runtime Draft Build - V3 Draw Feed (Draft Only)
- Timestamp (UTC): 2026-05-10T17:44:04Z
- Task scope:
  - Build validated draft runtime draw feed from DATABASE-aligned V3 draw truth.
  - Do not modify website files.
  - Do not overwrite production `processed_data` runtime feeds.
- Inputs:
  - data_truth/draw_results_truth/normalized/draw_results_long.csv
  - processed_data/draw_reality_engine.csv (comparison baseline only)
  - pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv
- Outputs:
  - data_model/runtime_drafts/draw_reality_engine_v2.csv
  - data_model/runtime_drafts/draw_reality_engine_v2_manifest.json
  - data_model/runtime_drafts/draw_reality_engine_v2_validation_report.json
  - data_model/runtime_drafts/draw_reality_engine_v2_vs_current_report.json
  - data_model/runtime_drafts/draw_reality_engine_v2_rows_added.csv
  - data_model/runtime_drafts/draw_reality_engine_v2_schema_changes.csv
- Validation results:
  - V3 rows: 112056
  - Draft rows: 112056
  - Corrected-key duplicates: 0
  - Required key blanks (`hunt_code`, `year`, `draw_pool`, `residency`, `points`): 0
  - DATABASE-matched rows missing boundary_id: 0
  - `HUNT_CODE_NOT_IN_2026_DATABASE` rows: 7167
  - `HUNT_CODE_NOT_IN_2026_DATABASE` unique hunt codes: 221
  - Current runtime rows: 36862
  - Rows added vs current runtime: 75194
  - Current runtime missing `draw_pool`: true
  - Core draw-value mismatches on overlapping rows: 0
- Promotion blockers:
  - Production `processed_data` not updated in this step.
  - Website runtime not updated in this step.
  - Downstream runtime consumers may need schema updates for `draw_pool`.
