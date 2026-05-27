# 2026 Draw Permit Subset

- Generated UTC: `2026-05-27T01:47:19+00:00`
- Draw-engine hunt codes: `1005`
- Promoted 2026 draw-permit subset codes: `995`
- Engine codes missing DATABASE: `0`
- Engine codes without numeric 2026 total: `10`

## Draw System Type Counts

- `BEAR_DRAW`: `101`
- `BONUS_ANTLERLESS_MOOSE`: `5`
- `BONUS_CWMU_BIG_GAME`: `279`
- `BONUS_LE_BIG_GAME`: `277`
- `BONUS_OIL_BIG_GAME`: `78`
- `BONUS_PLE_BIG_GAME`: `12`
- `BONUS_TURKEY`: `7`
- `PREFERENCE_ANTLERLESS_DEER`: `14`
- `PREFERENCE_ANTLERLESS_ELK`: `83`
- `PREFERENCE_DEDICATED_HUNTER_DEER`: `23`
- `PREFERENCE_DOE_PRONGHORN`: `8`
- `PREFERENCE_GENERAL_SEASON_BUCK_DEER`: `75`
- `PRIVATE_LANDS_ONLY_ANTLERLESS_ELK`: `27`
- `SPORTSMAN_PERMIT`: `5`
- `YOUTH_GENERAL_ANY_BULL_ELK`: `1`

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
| pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv | 995 | 0 | 0 |
| processed_data/hunt_master_enriched_2026_draw_subset.csv | 995 | 49930 | 211309 |
| processed_data/hunt_unit_reference_linked.csv | 995 | 0 | 0 |
| processed_data/point_ladder_view.csv | 995 | 0 | 0 |
| processed_data/draw_reality_engine.csv | 995 | 0 | 0 |
| processed_data/draw_reality_engine_predictive_v2.csv | 995 | 0 | 0 |
| processed_data/ml_draw_predictions_v1.csv | 995 | 0 | 0 |
| data/hunt-master-canonical-2026-database-candidate.csv | 995 | 0 | 0 |
| data/hunt-master-canonical-2026-source-of-truth.csv | 995 | 0 | 0 |
| processed_data/hunt-master-canonical-2026-source-of-truth.csv | 995 | 0 | 0 |
