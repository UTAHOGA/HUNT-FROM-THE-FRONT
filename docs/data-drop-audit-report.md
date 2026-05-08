# Data Drop Audit Report

Generated: 2026-05-08T15:46:38.775Z

## Promotion Rule Result

- DATABASE.csv green light: YES
- Promotion blockers found: 0

## Direct Comparison Summary

| Source file | Row count | Unique hunt codes | Missing in canonical | Extra in canonical | Source-only fields | Target-only fields | Changed shared fields | Difference type |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv | 1395 | 1394 | 0 | 0 | 0 | 43 | 1 | expected |
| pipeline/RAW/hunt_unit_database/2026/csv/hunt_master_canonical_2026_built.csv | 1289 | 1289 | 1 | 106 | 3 | 34 | 13 | derived |
| processed_data/hunt_master_enriched.csv | 53060 | 1394 | 0 | 0 | 18 | 38 | 5 | derived |
| data/hunt-master-canonical-2026-foundation.json | 1394 | 1394 | 0 | 0 | 0 | 0 | 0 | expected |

## Classified Missing Items

| Source | Hunt codes | Fields | Classification | Runtime impact | Promotion blocker | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| pipeline/RAW/hunt_unit_database/2026/csv/hunt_master_canonical_2026_built.csv | DB1276 |  | INTENTIONAL_LEGACY_DROP | No current runtime source list points to this built CSV; exclusion does not affect live planner/research pages. | false | This hunt_code appears only in an older built artifact and is absent from the current DATABASE.csv primary truth file. |
| pipeline/RAW/hunt_unit_database/2026/csv/hunt_master_canonical_2026_built.csv |  | avg_days_2026 | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| pipeline/RAW/hunt_unit_database/2026/csv/hunt_master_canonical_2026_built.csv |  | avg_points_2026 | INTENTIONAL_LEGACY_DROP | No current visitor-facing runtime impact. | false | Field appears only in an older/derived built artifact and is not referenced by the live runtime. |
| pipeline/RAW/hunt_unit_database/2026/csv/hunt_master_canonical_2026_built.csv |  | satisfaction_2026 | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | applicants_2025 | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | max_point_permits_2026 | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | missing_draw_data | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | missing_permits | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | missing_projection | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | odds_2025 | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | odds_2026_projected | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | points | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | projected_applicants_2026 | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | projected_applicants_2026_source | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | public_permits_2025 | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | public_permits_2026 | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | public_permits_2026_source | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | random_permits_2026 | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | residency | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | success_harvest | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | success_hunters | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |
| processed_data/hunt_master_enriched.csv |  | success_percent | SAFE_DERIVED_DROP | No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field. | false | Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract. |

## Promotion Blockers

None.
