# 2026 Permit Allocation Integrity Report

Generated: 2026-05-08T13:53:11.609Z
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
| processed_data/hunt_master_enriched.csv | 53060 | 1394 | 0 | 0 | 428432 | 0 | 0 |
| processed_data/hunt_unit_reference_linked.csv | 2788 | 1394 | 0 | 0 | 24720 | 0 | 0 |
| processed_data/draw_reality_engine.csv | 91588 | 1394 | 0 | 0 | 811600 | 0 | 0 |
| processed_data/point_ladder_view.csv | 91588 | 1394 | 0 | 0 | 811600 | 0 | 0 |
| data/hunt-master-canonical-2026-database-candidate.json | 1394 | 1394 | 0 | 0 | 12360 | 0 | 0 |
| data/hunt-master-canonical-2026-foundation.json | 1394 | 1394 | 0 | 0 | 12360 | 0 | 0 |
| data/hunt-master-canonical-2026-source-of-truth.json | 1394 | 1394 | 0 | 0 | 12360 | 0 | 0 |
| processed_data/hunt-master-canonical-2026-source-of-truth.json | 1394 | 1394 | 0 | 0 | 12360 | 0 | 0 |
| canonical/hunt-planner-2026.json | 1394 | 1394 | 0 | 0 | 12360 | 0 | 0 |
| generated/pages/hunt-planner.json | 1394 | 1394 | 0 | 0 | 12360 | 0 | 0 |
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

