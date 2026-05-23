# 2026 Permit Allocation Integrity Report

Generated: 2026-05-23T12:06:45.874Z
Source file used: pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv
Source label: DATABASE_2026_DWR_APPROVED_PUBLISHED_PERMIT_ALLOCATIONS
Promotion blockers: 0

## Status Counts

- FULL_SPLIT: 898
- TOTAL_ONLY: 351
- SPECIAL_PERMIT_ONLY: 0
- NO_QUOTA_PUBLISHED: 162
- PARTIAL_SPLIT: 0

## Files Audited

| File | Rows checked | Codes checked | Mismatches before | Mismatches after | Blank values preserved | Target-only codes | Database-only codes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| processed_data/hunt_master_enriched.csv | 54357 | 1411 | 156 | 0 | 436601 | 60 | 0 |
| processed_data/hunt_unit_reference_linked.csv | 2997 | 1411 | 156 | 0 | 25465 | 60 | 0 |
| processed_data/draw_reality_engine.csv | 36892 | 1411 | 156 | 0 | 257322 | 212 | 0 |
| processed_data/point_ladder_view.csv | 92844 | 1411 | 0 | 0 | 817951 | 60 | 0 |
| data/hunt-master-canonical-2026-database-candidate.json | 1411 | 1411 | 0 | 0 | 12454 | 0 | 0 |
| data/hunt-master-canonical-2026-foundation.json | 1394 | 1394 | 0 | 0 | 12335 | 0 | 17 |
| data/hunt-master-canonical-2026-source-of-truth.json | 1411 | 1411 | 0 | 0 | 12454 | 0 | 0 |
| processed_data/hunt-master-canonical-2026-source-of-truth.json | 1411 | 1411 | 0 | 0 | 12454 | 0 | 0 |
| canonical/hunt-planner-2026.json | 1411 | 1411 | 0 | 0 | 12454 | 0 | 0 |
| generated/pages/hunt-planner.json | 1411 | 1411 | 0 | 0 | 12454 | 0 | 0 |
| generated/pages/hunt-research.json | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Guardrails

- Allocation fields match DATABASE.csv: PASS
- Historical draw-result and harvest/performance fields are not accepted as allocation sources.
- TOTAL_ONLY rows may not contain inferred resident/nonresident splits.
- NO_QUOTA_PUBLISHED rows may not contain invented permit totals.
- SPECIAL_PERMIT_ONLY rows may contain special permit counts while remaining excluded from normal public draw permit totals.
- Source/provenance markers are required.

## Skipped Missing Targets

- None

