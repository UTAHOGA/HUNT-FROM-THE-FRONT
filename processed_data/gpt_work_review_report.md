# GPT Work Review Report

## Executive Summary
- Active repo reviewed: `C:\Users\tyler\Desktop\GitHub\HUNTS`
- `C:\Projects\HUNTS-main` was not used during this review pass.
- Forecast year verified: `2026`; source years verified: `2021,2022,2023,2024,2025`.
- Predictive artifacts are internally consistent on row count: `28860` rows in both `ml_draw_predictions_v1.csv` and `draw_reality_engine_predictive_v2.csv`.
- No stale `2027` output was found in the active 2026 processed artifacts. The only `2027` reference found is explanatory documentation in `docs/utah_bonus_predictive_engine.md`.
- Phase 7 turkey status: implemented, but one coverage-summary caveat remains.

## Phase-By-Phase Status
| Phase | Implemented | Current Status | Important Counts | Pass/Fail | Unresolved Issues |
| --- | --- | --- | --- | --- | --- |
| OIL / LE / PLE bonus engine | yes | MODELED_BONUS active for BONUS_OIL_BIG_GAME, BONUS_LE_BIG_GAME, BONUS_PLE_BIG_GAME | BONUS_OIL_BIG_GAME_rows=3311, BONUS_LE_BIG_GAME_rows=16402, BONUS_PLE_BIG_GAME_rows=529 | pass | none |
| Scope correction and target universe classifier | yes | Target classifier active; out-of-scope rows retained separately; excluded draw families classified distinctly. | out_of_scope_rows=908, target_scope_rows_seen_in_coverage=200685 | pass with reporting caveat | Coverage pending-family boolean for mountain lion/cougar is still row-driven instead of registry-driven. |
| General-season buck deer preference engine | yes | MODELED_PREFERENCE active | rows=715, hunt_codes=73 | pass with field-contract caveat | p_preference_draw is blank for this family even though p_draw/p_draw_pct are populated. |
| Antlerless deer / antlerless elk / doe pronghorn preference engine | yes | MODELED_PREFERENCE active | antlerless_deer_rows=100, antlerless_elk_rows=581, doe_pronghorn_rows=115 | pass with field-contract caveat | p_preference_draw is blank for these families even though p_draw/p_draw_pct are populated. |
| Dedicated Hunter deer preference engine | yes | MODELED_PREFERENCE active | rows=123, hunt_codes=22 | pass | none |
| CWMU public + antlerless moose + ewe bighorn bonus families | yes | MODELED_BONUS active with residual pending rows where source support or forecast inputs are incomplete. | cwmu_public_modeled_rows=3038, antlerless_moose_modeled_rows=36, ewe_bighorn_modeled_rows=14 | pass | none |
| Turkey bonus strategy and report-semantics cleanup | yes | BONUS_TURKEY modeled for proven limited-entry bonus turkey rows; report now separates active predictive and observed/history turkey counts. | bonus_turkey_modeled_rows=77, bonus_turkey_pending_rows=2, bonus_turkey_modeled_hunt_codes=7 | pass with one remaining coverage-summary caveat | Coverage summary still marks mountain_lion_cougar_still_pending false when the family is still unimplemented/pending. |
| Bear / private-lands-only antlerless elk / mountain lion-cougar / youth / random-only-OTC-landowner-mitigation families | no | Families remain classified and separated, but no new predictive strategy has been implemented in this review pass. | bear_pending_rows=2598, mountain_lion_pending_rows=0, private_lands_only_antlerless_elk_rows=0 | pending | No new strategy work was performed, by request. |

## Current Modeled Families
- `BONUS_OIL_BIG_GAME`: rows `3311`, hunt codes `79`, statuses `{'MODELED_BONUS': 3311}`
- `BONUS_LE_BIG_GAME`: rows `16402`, hunt codes `270`, statuses `{'MODELED_BONUS': 16402}`
- `BONUS_PLE_BIG_GAME`: rows `529`, hunt codes `9`, statuses `{'MODELED_BONUS': 529}`
- `BONUS_CWMU_BIG_GAME`: rows `3341`, hunt codes `271`, statuses `{'IN_SCOPE_MODEL_PENDING': 303, 'MODELED_BONUS': 3038}`
- `BONUS_ANTLERLESS_MOOSE`: rows `44`, hunt codes `5`, statuses `{'MODELED_BONUS': 36, 'IN_SCOPE_MODEL_PENDING': 8}`
- `BONUS_EWE_BIGHORN`: rows `14`, hunt codes `1`, statuses `{'MODELED_BONUS': 14}`
- `BONUS_TURKEY`: rows `79`, hunt codes `7`, statuses `{'MODELED_BONUS': 77, 'IN_SCOPE_MODEL_PENDING': 2}`
- `PREFERENCE_GENERAL_SEASON_BUCK_DEER`: rows `715`, hunt codes `73`, statuses `{'MODELED_PREFERENCE': 715}`
- `PREFERENCE_ANTLERLESS_DEER`: rows `100`, hunt codes `12`, statuses `{'MODELED_PREFERENCE': 100}`
- `PREFERENCE_ANTLERLESS_ELK`: rows `581`, hunt codes `80`, statuses `{'MODELED_PREFERENCE': 581}`
- `PREFERENCE_DOE_PRONGHORN`: rows `115`, hunt codes `8`, statuses `{'MODELED_PREFERENCE': 115}`
- `PREFERENCE_DEDICATED_HUNTER_DEER`: rows `123`, hunt codes `22`, statuses `{'MODELED_PREFERENCE': 123}`

## Pending Families
- `BEAR_DRAW`: rows `2598`, hunt codes `96`, statuses `{'IN_SCOPE_MODEL_PENDING': 2598}`
- `MOUNTAIN_LION_DRAW`: rows `0`, hunt codes `0`, statuses `{}`
- `PRIVATE_LANDS_ONLY_ANTLERLESS_ELK`: rows `0`, hunt codes `0`, statuses `{}`
- `YOUTH_GENERAL_DEER`: rows `0`, hunt codes `0`, statuses `{}`
- `YOUTH_GENERAL_ANY_BULL_ELK`: rows `0`, hunt codes `0`, statuses `{}`
- `GENERAL_BIG_GAME_OTHER`: rows `0`, hunt codes `0`, statuses `{}`
- `RANDOM_ONLY_TARGET`: rows `0`, hunt codes `0`, statuses `{}`
- `OTC_OR_REMAINING_TARGET`: rows `0`, hunt codes `0`, statuses `{}`
- `LANDOWNER_BIG_GAME`: rows `0`, hunt codes `0`, statuses `{}`
- `MITIGATION_OR_DEPREDATION_BIG_GAME`: rows `0`, hunt codes `0`, statuses `{}`

## Out-Of-Scope Families
- `OUT_OF_SCOPE_NON_TARGET`: rows `908`, hunt codes `23`

## Artifact Inventory
- `processed_data/ml_draw_predictions_v1.csv`
- `processed_data/ml_draw_predictions_v1_report.json`
- `processed_data/draw_reality_engine_predictive_v2.csv`
- `processed_data/draw_system_coverage_report.csv`
- `processed_data/draw_system_coverage_report.json`
- `processed_data/utah_bonus_predictive_manifest.json`
- `processed_data/backtest_utah_bonus_draw.csv`
- `processed_data/backtest_utah_bonus_draw_report.json`
- `processed_data/dedicated_hunter_predictions_v1.csv`
- `processed_data/dedicated_hunter_report.json`
- `processed_data/phase4_antlerless_validation_inventory.csv`
- `processed_data/phase4_antlerless_validation_inventory.json`
- `processed_data/phase6_bonus_special_predictions_v1.csv`
- `processed_data/phase6_bonus_special_report.json`
- `processed_data/turkey_bonus_predictions_v1.csv`
- `processed_data/turkey_bonus_report.json`

## Test Summary
- Command run: `python -m pytest tests/utah_bonus_predictive tests/utah_draw_predictive tests/utah/test_frontend_probability_selection.py`
- Passed: `63`
- Failed: `0`
- Blocked dependencies: none

## Known Issues
- `docs/utah_draw_system_scope.md`: Current State section is stale. It still lists Phase 3-7 families as pending even though the 2026 predictive artifacts and tests show them modeled. Next step: Refresh Utah docs to match the current 2026 modeled and pending family status before starting Phase 8.
- `processed_data/draw_system_coverage_report.json`: phase7_turkey.mountain_lion_cougar_still_pending is false because it is derived from active predictive rows rather than family registry status. The family remains unimplemented/pending even when there are zero active predictive rows. Next step: Patch coverage summary booleans so pending-family status comes from registry status, with row counts reported separately.
- `preference family field contract`: General-season buck deer and antlerless preference rows populate p_draw/p_draw_pct but leave p_preference_draw blank. Dedicated Hunter uses p_preference_draw correctly. This is a contract mismatch if preference families are expected to expose p_preference_draw uniformly. Next step: Decide whether to standardize p_preference_draw across all preference families or narrow the documented contract to Dedicated Hunter only.

## Recommended Next Step
- Recommended next implementation phase: `Phase 8: Bear strategy`.
- Recommended immediate cleanup before Phase 8: refresh the Utah docs and correct the coverage-summary pending-family boolean for mountain lion/cougar.
