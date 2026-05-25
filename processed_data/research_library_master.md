# Research Library Master

This is the governed research-library master generated from the existing library catalog.

## Status

- Status: `REVIEW_REQUIRED`
- Rows: `447`
- Source catalog rows: `328`
- Feeder file rows: `119`
- Direct DWR Hunt Planner CSV feeder rows: `88`
- Reviewed hunt-code rows: `0`
- Candidate hunt-code rows: `318`
- Unique candidate hunt codes: `147`
- Boundary-alignment feeder rows: `118`
- Rows missing source-year context: `8`
- Rows requiring review: `328`
- Blockers: `0`

## Law

- Every research library row must carry hunt_code and boundary_id columns.
- Blank reviewed hunt_code/boundary_id fields require explicit mapping status fields.
- Candidate hunt codes and candidate boundary IDs are not truth fields.
- DATABASE.csv is the canonical current hunt-code and boundary-id source.
- Direct Utah DWR Hunt Planner CSV-folder files are registered as source evidence.
- Feeder files are registered as source evidence with hashes before their values can be used.
- Do not promote 2025 permit values to 2026 available allotment without reviewed source-date context.
- Historical/current prefix changes must flow through the crosswalk before promotion.
- Document-level rows must be extracted into per-hunt-code rows before they can feed prediction/runtime data.

## Mapping Status Counts

- `DOCUMENT_LEVEL_MAPPING_REQUIRED`: `10`
- `FILE_LEVEL_REFERENCE_CONTAINS_OR_SUPPORTS_HUNT_CODES`: `119`
- `HISTORICAL_PREFIX_REVIEW_REQUIRED`: `318`

## Outputs

- `master_csv`: `data_truth/research_library_truth/normalized/research_library_master.csv`
- `master_json`: `data_truth/research_library_truth/normalized/research_library_master.json`
- `summary_json`: `data_truth/research_library_truth/validation/research_library_master_summary.json`
- `mapping_gaps_csv`: `data_truth/research_library_truth/validation/research_library_master_mapping_gaps.csv`
- `processed_csv`: `processed_data/research_library_master.csv`
- `processed_md`: `processed_data/research_library_master.md`
