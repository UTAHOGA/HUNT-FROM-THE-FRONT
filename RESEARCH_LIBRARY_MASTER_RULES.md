# Research Library Master Rules

This repository now treats research-library mapping as a truth-source contract.

## Mapping Law

- Every research-library row must include a `hunt_code` column and a `boundary_id` column.
- Every research-library row must include `hunt_code_mapping_status` and `boundary_id_mapping_status`.
- Blank reviewed `hunt_code` or `boundary_id` fields are allowed only when the status explains why they are blank.
- Candidate fields, including `candidate_hunt_code` and `candidate_boundary_id`, are evidence only. They are not truth fields.
- Fuzzy matches, old-prefix matches, and document-level matches must not be promoted into `hunt_code` or `boundary_id` without reviewed crosswalk evidence.
- Historical/current prefix changes must flow through `data_truth/crosswalk_truth/normalized/current_to_historical_hunt_code_crosswalk_2026.csv`.
- Document-level rows must be extracted into per-hunt-code rows before they can feed prediction, draw, harvest, runtime, or website-facing outputs.
- Any future document/database builder that creates research rows must preserve these columns and statuses.

## Current Status

The first governed build intentionally keeps the 2022-2024 conservation-permit rows as candidates only. Those rows are valuable evidence, but the first-letter/prefix changes around 2023-2024 mean they cannot be treated as reviewed current hunt-code truth without crosswalk review.
