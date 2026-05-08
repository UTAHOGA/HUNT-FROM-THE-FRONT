# 2026 Permit Allocation Integrity Report

Generated: 2026-05-08T11:48:36.121Z
Source file used: pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv
Source label: DATABASE_2026_DWR_APPROVED_PUBLISHED_PERMIT_ALLOCATIONS
Promotion blockers: 0

## Status Counts

- FULL_SPLIT: 880
- TOTAL_ONLY: 194
- SPECIAL_PERMIT_ONLY: 27
- NO_QUOTA_PUBLISHED: 293
- PARTIAL_SPLIT: 0

## Files Audited

| File | Rows checked | Codes checked | Mismatches before | Mismatches after | Blank values preserved | Target-only codes | Database-only codes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| processed_data/hunt_master_enriched.csv | 53782 | 1089 | 0 | 0 | 422488 | 26 | 305 |
| processed_data/hunt_unit_reference_linked.csv | 2668 | 1289 | 0 | 0 | 23034 | 45 | 105 |
| processed_data/draw_reality_engine.csv | 73174 | 1089 | 0 | 0 | 615448 | 26 | 305 |
| processed_data/point_ladder_view.csv | 73174 | 1089 | 0 | 0 | 615448 | 26 | 305 |
| data/hunt-master-canonical-2026-foundation.json | 1394 | 1394 | 0 | 0 | 12360 | 0 | 0 |
| data/hunt-master-canonical-2026-source-of-truth.json | 1394 | 1394 | 0 | 0 | 12360 | 0 | 0 |
| processed_data/hunt-master-canonical-2026-source-of-truth.json | 1394 | 1394 | 0 | 0 | 12360 | 0 | 0 |

## Guardrails

- Allocation fields match DATABASE.csv: PASS
- Historical draw-result and harvest/performance fields are not accepted as allocation sources.
- TOTAL_ONLY rows may not contain inferred resident/nonresident splits.
- NO_QUOTA_PUBLISHED rows may not contain invented permit totals.
- SPECIAL_PERMIT_ONLY rows may contain special permit counts while remaining excluded from normal public draw permit totals.
- Source/provenance markers are required.

## Skipped Missing Targets

- data/hunt-master-canonical-2026-database-candidate.json
- canonical/hunt-planner-2026.json
- generated/pages/hunt-planner.json
- generated/pages/hunt-research.json

