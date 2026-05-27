# 2026 Draw Permit Subset

- Generated UTC: `2026-05-27T03:41:26+00:00`
- Draw-engine hunt codes: `863`
- Promoted 2026 draw-permit subset codes: `813`
- Engine codes missing DATABASE: `0`
- Engine codes without numeric 2026 total: `50`

## Draw System Type Counts

- `BEAR_DRAW`: `101`
- `BONUS_ANTLERLESS_MOOSE`: `5`
- `BONUS_CWMU_BIG_GAME`: `279`
- `BONUS_EWE_BIGHORN`: `1`
- `BONUS_LE_BIG_GAME`: `277`
- `BONUS_OIL_BIG_GAME`: `78`
- `BONUS_PLE_BIG_GAME`: `12`
- `BONUS_TURKEY`: `2`
- `PREFERENCE_DEDICATED_HUNTER_DEER`: `23`
- `PREFERENCE_GENERAL_SEASON_BUCK_DEER`: `2`
- `PRIVATE_LANDS_ONLY_ANTLERLESS_ELK`: `27`
- `SPORTSMAN_PERMIT`: `5`
- `YOUTH_DRAW_ONLY_ELK`: `1`

## Spot Checks

| File | Hunt code | Res | NR | Total | Source | Draw type |
| --- | --- | ---: | ---: | ---: | --- | --- |
| pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv | EB3022 | 130 | 15 | 145 | 2026_LIVE_DWR_HUNT_PLANNER_COMPREHENSIVE | BONUS_LE_BIG_GAME |
| pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv | DB1002 | 1 | 0 | 1 | 2026_LIVE_DWR_HUNT_PLANNER_COMPREHENSIVE | BONUS_PLE_BIG_GAME |
| pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv | BI6528 | 6 | 0 | 6 | 2026_LIVE_DWR_HUNT_PLANNER_COMPREHENSIVE | BONUS_OIL_BIG_GAME |
| pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv | EA2012 |  |  | 400 | 2026_LIVE_DWR_HUNT_PLANNER_COMPREHENSIVE | PRIVATE_LANDS_ONLY_ANTLERLESS_ELK |
| pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv | CG9999 |  |  |  |  |  |
| processed_data/ml_draw_predictions_v1.csv | EB3022 | 130 | 15 | 145 | 2026_LIVE_DWR_HUNT_PLANNER_COMPREHENSIVE | BONUS_LE_BIG_GAME |

## Promotion Targets

| File | Matched codes | Rows changed | Changed cells |
| --- | ---: | ---: | ---: |
| pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv | 813 | 0 | 0 |
| processed_data/hunt_master_enriched_2026_draw_subset.csv | 813 | 0 | 0 |
| processed_data/hunt_unit_reference_linked.csv | 813 | 0 | 0 |
| processed_data/point_ladder_view.csv | 813 | 0 | 0 |
| processed_data/draw_reality_engine.csv | 813 | 0 | 0 |
| processed_data/draw_reality_engine_predictive_v2.csv | 813 | 26294 | 124159 |
| processed_data/ml_draw_predictions_v1.csv | 813 | 26294 | 124159 |
| data/hunt-master-canonical-2026-database-candidate.csv | 813 | 0 | 0 |
| data/hunt-master-canonical-2026-source-of-truth.csv | 813 | 0 | 0 |
| processed_data/hunt-master-canonical-2026-source-of-truth.csv | 813 | 0 | 0 |
