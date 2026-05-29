# Mule Deer Statewide Plan Foundational Reference

Source: `pipeline/RAW/hunt_unit_database/mule_deer_plan.pdf`
Generated: 2026-05-29T00:18:06.065Z

Persistent foundational policy reference for HUNT-BUILDER.

| Key ID | Topic | Metric | Value | Unit | Plan Page |
|---|---|---|---|---|---|
| MD_PLAN_SCOPE_2024_2030 | Plan Scope | Plan Effective Period | December 2024 through December 2030 | date range | 2 |
| MD_POP_OBJ_STATEWIDE | Population Objective | Statewide Population Objective | 404900 | deer | 11 |
| MD_POSTSEASON_2023_EST | Population Status | 2023 Postseason Population Estimate | 279000 | deer | 6 |
| MD_GENERAL_RATIO_OBJECTIVE | Harvest Structure | General Season Buck-to-Doe Objective | 15-17 or 18-20 | bucks per 100 does | 24 |
| MD_LIMITED_ENTRY_RATIO_OBJECTIVE | Harvest Structure | Limited Entry Buck-to-Doe Objective | 25-30 | bucks per 100 does | 25 |
| MD_PREMIUM_LE_RATIO_OBJECTIVE | Harvest Structure | Premium Limited Entry Buck-to-Doe Objective | 40-45 | bucks per 100 does | 25 |
| MD_PERMIT_AUTOMATIC_DELTA | Permit Governance | Automatic Annual Permit Change Threshold | 20 | percent | 24-25 |
| MD_WEAPON_SPLIT_STANDARD | Permit Allocation | Standard Weapon Split | 20/20/60 | archery/muzzleloader/any weapon percent | 26 |
| MD_WEAPON_SPLIT_EARLY_AW | Permit Allocation | Split When Early Any Weapon Added | 20/20/20/40 | archery/muzzleloader/early any/late any percent | 26 |
| MD_MULTI_SEASON_SHARE | Permit Allocation | Multi-season Permit Share | 3 | percent of hunters | 26 |
| MD_LATE_MUZZLELOADER_GENERAL_UNITS | Hunt Opportunity | Late Muzzleloader on General Units | up to 0.5% with minimum 5 permits per unit | permit rule | 26 |
| MD_PREMIUM_MGMT_BUCK_SHARE | Premium LE Policy | Management Buck Permit Share | 10-20 | percent of premium LE permits | 26 |
| MD_PERMITS_GENERAL_2024 | Recent Baseline | General-season permits available | 71525 | permits | 4 |
| MD_HARVEST_10YR_AVG | Recent Baseline | 10-year average buck harvest | 25062 | bucks per year | 5 |
| MD_HUNTER_SUCCESS_2023 | Recent Baseline | General-season any-weapon hunter success | 35.0 | percent | 5 |
| MD_ADULT_FEMALE_SURVIVAL_10YR | Monitoring Metrics | Adult female survival average | 79.8 | percent | 7 |
| MD_FAWN_SURVIVAL_10YR | Monitoring Metrics | Fawn survival average | 52.1 | percent | 7 |
| MD_MIN_DOE_CLASSIFICATION | Monitoring Metrics | Minimum does classified per unit | 400 | does | 7 |
| MD_HABITAT_ACRE_TARGET | Habitat Objective | Crucial range improvement target by 2030 | 600000 | acres | 22 |
| MD_DRAW_ODDS_LE_2024_RESIDENT | Demand Pressure | Resident odds drawing LE buck permit | 1 in 25.4 | odds | 18/50 |
| MD_DRAW_ODDS_GENERAL_2024 | Demand Pressure | General-season draw odds | 1 in 2.3 | odds | 18/50 |
| MD_CWD_ACTION_THRESHOLD | CWD Management | CWD management action threshold | detection of first positive (about 1% prevalence surveillance target) | policy threshold | 59 |
| MD_CWD_SAMPLE_SIZE_95CI | CWD Surveillance | Sample size for at least 1% prevalence detection at 95% confidence | 304 deer and 346 elk | samples | 57 |
| MD_INTERNAL_USAGE_RULE | Data Governance | Age metrics policy boundary | Use age metrics for quality context only; not direct permit quota or p_draw overrides | rule | derived |

## Usage Rules
- Use this file for recurring policy and management context.
- Do not use it to overwrite canonical permit truth in DATABASE.csv.
- Do not convert policy values directly to p_draw without explicit model validation.
