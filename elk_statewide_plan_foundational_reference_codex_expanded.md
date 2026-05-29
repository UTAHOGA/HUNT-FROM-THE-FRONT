# Elk Statewide Plan Foundational Reference

Source: `pipeline/RAW/hunt_unit_database/elk_plan.pdf`  
Generated: 2026-05-29T00:34:14.702Z  
Reviewed/expanded: 2026-05-29T00:44:12Z

Persistent foundational policy/reference layer for HUNTS/HUNT-BUILDER workflows.

> **Classification correction:** This file is an elk statewide management-plan reference. It is not raw hunt-code harvest truth, not permit truth, and not draw-odds truth. It should be read by Codex as policy, management context, age-objective context, demand context, and engine guardrails.

## Codex Operating Rules

When Codex reads this file, apply these hard rules:

1. **Do not overwrite `DATABASE.csv`.** The plan may describe permit strategies and objectives, but the canonical current permit and hunt-code truth remains `pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv`.
2. **Do not convert plan demand figures into `p_draw`.** Values such as 2022 LE odds, general sellout time, or applicants-per-permit are demand-pressure context, not modeled probability.
3. **Do not use plan age objectives as harvested-age observations.** Age objective bands such as `6.5-7.0`, `6.0-6.5`, and `5.5-6.0` are management targets. Actual `average_harvest_age` must come from annual report age tables or species-report mean-age tables.
4. **Do not use age metrics to directly override permit quotas.** Use age/quality context for quality scoring, display, and validation gates only.
5. **Keep general-season, LE, adaptive opportunity, and antlerless strategies separate.** These are different management lanes.
6. **Preserve source lineage.** Every extracted policy datum should retain `source_document`, `source_page`, and `evidence_excerpt`.
7. **Treat all values in this file as plan-context unless a later deterministic script explicitly promotes a derived field after validation.**

## Recommended Engine Placement

| Engine Layer | Use This File? | Use |
|---|---:|---|
| `DATABASE.csv` permit truth | No | Never overwrite current official hunt/permit rows. |
| Draw probability / `p_draw` | No direct use | Demand metrics may explain pressure but must not replace simulator outputs. |
| Quality score | Yes, limited | Use LE age objectives, biological basis, and harvest-performance context as weighting guidance. |
| Research page | Yes | Display policy context, age-objective categories, demand pressure, and opportunity strategy. |
| Validation gates | Yes | Use plan gates such as age objective + 3-year any-weapon success threshold as review flags, not automatic permit changes. |
| Harvest-age backfill | No direct values | Use plan age-objective bands only to interpret actual harvested-age rows from annual reports. |

## High-Value Codex Follow-Up Tasks

1. **Create a normalized companion CSV** from this file with columns:
   `key_id, data_class, metric, display_value, numeric_value, min_value, max_value, unit, scope, year, model_use, prohibited_use, source_page, evidence_excerpt`.

2. **Split compound values into machine fields.**
   - `6.5-7.0; 6.0-6.5; 5.5-6.0` should become three LE age categories.
   - `25/15/60` should become `archery_pct=25`, `muzzleloader_pct=15`, `any_legal_weapon_pct=60`.
   - `10/30/17 plus 3 multi-season` should become `early_any_weapon_pct=10`, `mid_any_weapon_pct=30`, `late_any_weapon_pct=17`, `multi_season_pct=3`.
   - `1:19.8 resident; 1:70.5 nonresident` should become `resident_odds_ratio=19.8`, `nonresident_odds_ratio=70.5`, with `display_only=true`.

3. **Wire plan context into quality-score documentation before engine scoring.**
   - LE quality is legitimately age-objective based.
   - Age objective categories are targets, not observed age.
   - Actual observed age should come from `harvest_age_features_by_hunt_code_latest.csv`.

4. **Add a validation-only check for LE units.**
   Flag rows where:
   - actual 3-year average harvested age is below plan objective band; or
   - any-legal-weapon 3-year success exceeds 75% and age objective is met/exceeded.
   Do not automatically adjust permits.

5. **Add research-page context cards.**
   Create public-facing cards for:
   - “Why elk age matters”
   - “Why LE elk age objectives differ by unit”
   - “What demand pressure means”
   - “Why age does not directly equal draw odds”

## Key Model Design Interpretation

The elk plan is unusually important because it explicitly treats traditional limited-entry elk units as average-age managed. Therefore, for elk only, `average_harvest_age` is not merely a trophy curiosity; it is a core quality-management signal. However, the plan still does not give hunt-code-level observed age. Observed age must come from annual report age tables and then be crosswalked to hunt codes.

Recommended elk quality-score feature treatment:

```text
elk_age_quality_score =
  compare actual average_harvest_age_3yr or latest average_harvest_age
  against the plan objective band for that unit/category.

Never:
  - treat plan objective band as actual harvested age
  - use age objective to overwrite p_draw
  - use age objective to overwrite permit quota
```

## Data-Class Definitions

| Data Class | Meaning | Use |
|---|---|---|
| `plan_governance` | Plan dates, mid-plan review timing | Change monitoring and active-policy context |
| `population_context` | Population estimate/objective, growth, survival, reproduction | Context features and research display |
| `harvest_context` | General harvest/success baselines | Context feature, not hunt-code truth |
| `draw_demand_context` | Applicants, odds ratios, sellout timing | Demand-pressure display only |
| `permit_policy` | Permit allocation/governance strategy | Validation context, not direct permit truth |
| `quality_structure_context` | Age objective and biological maturity rationale | Quality-score design guidance |
| `habitat_context` | Habitat treatment/mitigation goals | Long-horizon context only |
| `governance_rule` | Explicit engine/data-use restrictions | Hard guardrail |

## Original Foundational Reference Table

| Key ID | Topic | Metric | Value | Unit | Plan Page |
|---|---|---|---|---|---|
| ELK_PLAN_SCOPE_2022_2032 | Plan Scope | Plan Effective Period | December 2022 through December 2032 | date range | 2 |
| ELK_MIDPLAN_REVIEW_2026 | Plan Governance | Mid-plan review timing | Spring 2026 | scheduled review | 2 |
| ELK_STATEWIDE_POP_EST | Population Status | Current statewide elk population estimate | 84390 | elk | 5 |
| ELK_STATEWIDE_POP_OBJECTIVE | Population Objective | Statewide population objective (sum of unit objectives) | 78990 | elk | 10 |
| ELK_HISTORIC_GROWTH_1975_1990 | Population Trend | Historical growth from 1975 to 1990 | 18000 to 58000 (annual growth rate 1.08) | elk and growth rate | 5 |
| ELK_GENERAL_PERMITS_2022_TOTAL | General Season Opportunity | General season permits issued | over 47000 | permits | 4 |
| ELK_GENERAL_PERMITS_2022_BREAKDOWN | General Season Opportunity | 2022 permit mix breakdown | 17500 adult any bull; over 2200 youth any bull; 15000 spike; over 12700 archery | permits | 4 |
| ELK_GENERAL_SUCCESS_2021 | Harvest Performance | General season hunter success (all general season elk hunts) | 15.5 | percent | 4 |
| ELK_GENERAL_2021_HARVEST_HUNTERS | Harvest Performance | General season harvest and hunters afield | 5755 harvested by 37211 hunters | elk and hunters | 4 |
| ELK_ARCHERY_SUCCESS_2021 | Harvest Performance | Archery hunter success | 11.4 | percent | 4 |
| ELK_MULTI_SEASON_SUCCESS_SPIKE | Harvest Performance | Multi-season spike success | 22.9 | percent | 4 |
| ELK_MULTI_SEASON_SUCCESS_ANY_BULL | Harvest Performance | Multi-season any bull success | 28.2 | percent | 4 |
| ELK_LE_AGE_MANAGEMENT_CORE | Limited Entry Management | Traditional LE units managed by average age of harvested bulls | true | policy | 4 |
| ELK_ANTLER_GROWTH_96_BY_6_5 | Biological Basis | Average antler growth achieved by age 6.5 | 96 | percent | 4 |
| ELK_MAINBEAM_97_BY_6_5 | Biological Basis | Main beam length achieved by age 6.5 | 97 | percent | 4 |
| ELK_ANTLER_PLATEAU_AFTER_8_5 | Biological Basis | Main beam length increase after age 8.5 | no increase | trend | 4 |
| ELK_OPPORTUNITY_FROM_LOWERING_AGE_OBJ | Permit Governance | Estimated opportunity gain from lowering age objectives by one year | 40-50 | percent | 4 |
| ELK_ADULT_COW_SURV_WITH_HARVEST | Survival Metrics | Adult female annual survival including harvest | 75-81 | percent | 6 |
| ELK_ADULT_COW_SURV_NO_HARVEST | Survival Metrics | Adult female annual survival excluding human harvest | 93-98 | percent | 6 |
| ELK_ADULT_MORTALITY_SHARE_HUNTER | Mortality Drivers | Share of collared adult females killed by hunters | over 21 | percent | 6 |
| ELK_CALF_SURVIVAL_FIRST_YEAR | Survival Metrics | Neonate survival during first year | 41-47 | percent | 6 |
| ELK_CALF_MORTALITY_COUGAR_SHARE | Mortality Drivers | Collared calf first-year mortality attributed to cougars | up to 45 | percent | 6 |
| ELK_PREGNANCY_RATE_AVG | Reproduction Metrics | Average adult pregnancy rate | 85 | percent | 6 |
| ELK_PREGNANCY_RATE_RANGE | Reproduction Metrics | Adult pregnancy rate range | 55-100 | percent | 6 |
| ELK_PRIVATE_LANDS_ONLY_ANTLERLESS_2016 | Distribution Management | Private-lands-only antlerless permit implementation year | 2016 | year | 8 |
| ELK_LE_DEMAND_2022_APPLICANTS_PERMITS | Demand Pressure | Limited entry applicants and permits | 75925 applicants for 3117 permits | applicants and permits | 17 |
| ELK_LE_DRAW_ODDS_2022 | Demand Pressure | Limited entry draw odds in 2022 | 1:19.8 resident; 1:70.5 nonresident | odds | 17 |
| ELK_ANY_BULL_SELL_OUT_ACCEL | Demand Pressure | General season any bull permit sellout acceleration | 2018 sold out in 34 days; 2020 in less than 8 hours; 2022 in less than 6 hours | time-to-sellout | 17 |
| ELK_SPIKE_SELL_OUT_2022 | Demand Pressure | General season spike sellout timing | 9 hours | time-to-sellout | 17 |
| ELK_GENERAL_OPPORTUNITY_TARGETS | General Season Strategy | Statewide opportunity targets | 15000 spike permits; up to 4500 multi-season sub-quota; up to 15000 early any-bull permits; unlimited late any-bull; unlimited general archery | permit strategy | 22 |
| ELK_YOUTH_GENERAL_OPPORTUNITY | Youth Strategy | Youth general season opportunity | unlimited general season youth bull permits on spike and any-bull units; separate limited draw-only youth any-bull hunt | permit strategy | 22 |
| ELK_LE_AGE_CATEGORIES | Limited Entry Strategy | Traditional LE age objective categories | 6.5-7.0; 6.0-6.5; 5.5-6.0 | years average age of harvest | 22 |
| ELK_LE_PERMIT_INCREASE_GATE | Limited Entry Strategy | Condition for increasing LE permits while maintaining quality | any-legal-weapon 3-year average success over 75% and unit meeting/exceeding age objective | rule threshold | 22 |
| ELK_LE_WEAPON_ALLOCATION_STANDARD | Limited Entry Strategy | Traditional LE weapon allocation | 25/15/60 | archery/muzzleloader/any legal weapon percent | 23 |
| ELK_LE_ANY_WEAPON_SEASON_SPLIT | Limited Entry Strategy | Any-weapon split when all three seasons exist | 10/30/17 plus 3 multi-season | early/mid/late any-weapon and multi-season percent | 23 |
| ELK_PRIMITIVE_WEAPON_SPLIT | Restricted Weapons Strategy | Primitive weapon LE allocation | 50/50 | September archery versus HAMS/restricted weapon percent | 23 |
| ELK_ADAPTIVE_OPPORTUNITY_PERMIT_RULE | Adaptive Opportunity Hunts | Late-season adaptive permit sizing rule | 1% of combined LE permits or minimum 5 permits | permit rule | 23 |
| ELK_HIGH_BULL_COW_TRIGGER_RESTRICTED | Adaptive Opportunity Hunts | Restricted/HAMS recommendation trigger | bull:cow ratio greater than 40 bulls per 100 cows | ratio threshold | 23 |
| ELK_HABITAT_FORAGE_TREATMENT_TARGET | Habitat Management | Annual forage treatment target | minimum 40000 | acres per year | 21 |
| ELK_HABITAT_MITIGATION_RATIO | Habitat Management | Voluntary mitigation ratio for disturbance in crucial habitat | 4:1 | acres improved or conserved per acre disturbed | 21 |
| ELK_INTERNAL_USAGE_RULE | Data Governance | Age metrics policy boundary | Use age metrics for quality context only; do not directly override permit quotas or p_draw | rule | derived |

## Codex Data-Use Classification Table

| Key ID | Data Class | Recommended Model Use | Prohibited Use | Normalization Suggestion |
|---|---|---|---|---|
| ELK_PLAN_SCOPE_2022_2032 | plan_governance | policy_context | Active-plan metadata | Keep source lineage and display value. |
| ELK_MIDPLAN_REVIEW_2026 | plan_governance | policy_context | Active-plan metadata | Keep source lineage and display value. |
| ELK_STATEWIDE_POP_EST | population_context | context_feature | Do not use as hunt-code harvest truth | Keep source lineage and display value. |
| ELK_STATEWIDE_POP_OBJECTIVE | population_context | context_feature | Do not use as hunt-code harvest truth | Keep source lineage and display value. |
| ELK_HISTORIC_GROWTH_1975_1990 | population_context | context_feature | Do not use as hunt-code harvest truth | Keep source lineage and display value. |
| ELK_GENERAL_PERMITS_2022_TOTAL | review | review | Review before model use | Keep source lineage and display value. |
| ELK_GENERAL_PERMITS_2022_BREAKDOWN | review | review | Review before model use | Keep source lineage and display value. |
| ELK_GENERAL_SUCCESS_2021 | harvest_context | context_feature | No direct p_draw or quota override | Keep source lineage and display value. |
| ELK_GENERAL_2021_HARVEST_HUNTERS | harvest_context | context_feature | No direct p_draw or quota override | Keep source lineage and display value. |
| ELK_ARCHERY_SUCCESS_2021 | harvest_context | context_feature | No direct p_draw or quota override | Keep source lineage and display value. |
| ELK_MULTI_SEASON_SUCCESS_SPIKE | harvest_context | context_feature | No direct p_draw or quota override | Keep source lineage and display value. |
| ELK_MULTI_SEASON_SUCCESS_ANY_BULL | harvest_context | context_feature | No direct p_draw or quota override | Keep source lineage and display value. |
| ELK_LE_AGE_MANAGEMENT_CORE | permit_policy | policy_context | Use only as governance/validation context | Keep source lineage and display value. |
| ELK_ANTLER_GROWTH_96_BY_6_5 | quality_structure_context | quality_context | Use to explain trophy-age scoring logic, not raw age truth | Use to interpret observed age metrics; do not treat as observed age. |
| ELK_MAINBEAM_97_BY_6_5 | quality_structure_context | quality_context | Use to explain trophy-age scoring logic, not raw age truth | Use to interpret observed age metrics; do not treat as observed age. |
| ELK_ANTLER_PLATEAU_AFTER_8_5 | quality_structure_context | quality_context | Use to explain trophy-age scoring logic, not raw age truth | Use to interpret observed age metrics; do not treat as observed age. |
| ELK_OPPORTUNITY_FROM_LOWERING_AGE_OBJ | permit_policy | policy_context | Use only as governance/validation context | Split range into min/max numeric fields where possible. |
| ELK_ADULT_COW_SURV_WITH_HARVEST | population_context | context_feature | Do not use as hunt-code harvest truth | Split range into min/max numeric fields where possible. |
| ELK_ADULT_COW_SURV_NO_HARVEST | population_context | context_feature | Do not use as hunt-code harvest truth | Split range into min/max numeric fields where possible. |
| ELK_ADULT_MORTALITY_SHARE_HUNTER | population_context | context_feature | Do not use as hunt-code harvest truth | Keep source lineage and display value. |
| ELK_CALF_SURVIVAL_FIRST_YEAR | population_context | context_feature | Do not use as hunt-code harvest truth | Split range into min/max numeric fields where possible. |
| ELK_CALF_MORTALITY_COUGAR_SHARE | population_context | context_feature | Do not use as hunt-code harvest truth | Keep source lineage and display value. |
| ELK_PREGNANCY_RATE_AVG | population_context | context_feature | Do not use as hunt-code harvest truth | Keep source lineage and display value. |
| ELK_PREGNANCY_RATE_RANGE | population_context | context_feature | Do not use as hunt-code harvest truth | Split range into min/max numeric fields where possible. |
| ELK_PRIVATE_LANDS_ONLY_ANTLERLESS_2016 | population_context | context_feature | Do not use as hunt-code harvest truth | Keep source lineage and display value. |
| ELK_LE_DEMAND_2022_APPLICANTS_PERMITS | draw_demand_context | display_context | Do not treat as modeled odds | Keep as demand display/context; add numeric ratio fields only if clearly parseable. |
| ELK_LE_DRAW_ODDS_2022 | draw_demand_context | display_context | Do not treat as modeled odds | Keep as demand display/context; add numeric ratio fields only if clearly parseable. |
| ELK_ANY_BULL_SELL_OUT_ACCEL | draw_demand_context | display_context | Do not treat as modeled odds | Keep as demand display/context; add numeric ratio fields only if clearly parseable. |
| ELK_SPIKE_SELL_OUT_2022 | draw_demand_context | display_context | Do not treat as modeled odds | Keep source lineage and display value. |
| ELK_GENERAL_OPPORTUNITY_TARGETS | permit_policy | policy_context | Use only as governance/validation context | Split range into min/max numeric fields where possible. |
| ELK_YOUTH_GENERAL_OPPORTUNITY | permit_policy | policy_context | Use only as governance/validation context | Keep source lineage and display value. |
| ELK_LE_AGE_CATEGORIES | permit_policy | policy_context | Use only as governance/validation context | Split range into min/max numeric fields where possible. |
| ELK_LE_PERMIT_INCREASE_GATE | permit_policy | policy_context | Use only as governance/validation context | Split range into min/max numeric fields where possible. |
| ELK_LE_WEAPON_ALLOCATION_STANDARD | permit_policy | policy_context | Use only as governance/validation context | Split percentage string into named numeric percentage fields. |
| ELK_LE_ANY_WEAPON_SEASON_SPLIT | permit_policy | policy_context | Use only as governance/validation context | Split percentage string into named numeric percentage fields. |
| ELK_PRIMITIVE_WEAPON_SPLIT | permit_policy | policy_context | Use only as governance/validation context | Split percentage string into named numeric percentage fields. |
| ELK_ADAPTIVE_OPPORTUNITY_PERMIT_RULE | permit_policy | policy_context | Use only as governance/validation context | Keep source lineage and display value. |
| ELK_HIGH_BULL_COW_TRIGGER_RESTRICTED | permit_policy | policy_context | Use only as governance/validation context | Keep as demand display/context; add numeric ratio fields only if clearly parseable. |
| ELK_HABITAT_FORAGE_TREATMENT_TARGET | habitat_context | context_feature | Long-horizon context only | Keep source lineage and display value. |
| ELK_HABITAT_MITIGATION_RATIO | habitat_context | context_feature | Long-horizon context only | Keep as demand display/context; add numeric ratio fields only if clearly parseable. |
| ELK_INTERNAL_USAGE_RULE | governance_rule | hard_rule | Must be enforced | Enforce as hard guardrail. |

## Row-Level Deep-Read Notes

### ELK_PLAN_SCOPE_2022_2032
- **Topic:** Plan Scope
- **Metric:** Plan Effective Period
- **Value:** `December 2022 through December 2032` `date range`
- **Plan page:** 2
- **Evidence excerpt:** Approved on December 1, 2022 and in effect for 10 years until December 2032.
- **Codex use:** policy_context / `plan_governance`.
- **Do not:** Active-plan metadata.
- **Suggestion:** Keep source lineage and display value.

### ELK_MIDPLAN_REVIEW_2026
- **Topic:** Plan Governance
- **Metric:** Mid-plan review timing
- **Value:** `Spring 2026` `scheduled review`
- **Plan page:** 2
- **Evidence excerpt:** Two mid-plan reviews spaced 3-4 years apart, scheduled in spring 2026.
- **Codex use:** policy_context / `plan_governance`.
- **Do not:** Active-plan metadata.
- **Suggestion:** Keep source lineage and display value.

### ELK_STATEWIDE_POP_EST
- **Topic:** Population Status
- **Metric:** Current statewide elk population estimate
- **Value:** `84390` `elk`
- **Plan page:** 5
- **Evidence excerpt:** Current statewide population estimated at approximately 84,390 animals.
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Keep source lineage and display value.

### ELK_STATEWIDE_POP_OBJECTIVE
- **Topic:** Population Objective
- **Metric:** Statewide population objective (sum of unit objectives)
- **Value:** `78990` `elk`
- **Plan page:** 10
- **Evidence excerpt:** Current population objective for elk statewide is 78,990.
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Keep source lineage and display value.

### ELK_HISTORIC_GROWTH_1975_1990
- **Topic:** Population Trend
- **Metric:** Historical growth from 1975 to 1990
- **Value:** `18000 to 58000 (annual growth rate 1.08)` `elk and growth rate`
- **Plan page:** 5
- **Evidence excerpt:** Population grew from about 18,000 to 58,000 (average annual growth rate 1.08).
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Keep source lineage and display value.

### ELK_GENERAL_PERMITS_2022_TOTAL
- **Topic:** General Season Opportunity
- **Metric:** General season permits issued
- **Value:** `over 47000` `permits`
- **Plan page:** 4
- **Evidence excerpt:** Issued over 47,000 general season permits in 2022.
- **Codex use:** review / `review`.
- **Do not:** Review before model use.
- **Suggestion:** Keep source lineage and display value.

### ELK_GENERAL_PERMITS_2022_BREAKDOWN
- **Topic:** General Season Opportunity
- **Metric:** 2022 permit mix breakdown
- **Value:** `17500 adult any bull; over 2200 youth any bull; 15000 spike; over 12700 archery` `permits`
- **Plan page:** 4
- **Evidence excerpt:** Permit categories listed for adult any bull, youth any bull, spike, and archery.
- **Codex use:** review / `review`.
- **Do not:** Review before model use.
- **Suggestion:** Keep source lineage and display value.

### ELK_GENERAL_SUCCESS_2021
- **Topic:** Harvest Performance
- **Metric:** General season hunter success (all general season elk hunts)
- **Value:** `15.5` `percent`
- **Plan page:** 4
- **Evidence excerpt:** Success rates in 2021 averaged 15.5% across general season elk hunts.
- **Codex use:** context_feature / `harvest_context`.
- **Do not:** No direct p_draw or quota override.
- **Suggestion:** Keep source lineage and display value.

### ELK_GENERAL_2021_HARVEST_HUNTERS
- **Topic:** Harvest Performance
- **Metric:** General season harvest and hunters afield
- **Value:** `5755 harvested by 37211 hunters` `elk and hunters`
- **Plan page:** 4
- **Evidence excerpt:** 5,755 elk harvested by 37,211 hunters afield.
- **Codex use:** context_feature / `harvest_context`.
- **Do not:** No direct p_draw or quota override.
- **Suggestion:** Keep source lineage and display value.

### ELK_ARCHERY_SUCCESS_2021
- **Topic:** Harvest Performance
- **Metric:** Archery hunter success
- **Value:** `11.4` `percent`
- **Plan page:** 4
- **Evidence excerpt:** Archery hunters recorded the lowest success rates (11.4%).
- **Codex use:** context_feature / `harvest_context`.
- **Do not:** No direct p_draw or quota override.
- **Suggestion:** Keep source lineage and display value.

### ELK_MULTI_SEASON_SUCCESS_SPIKE
- **Topic:** Harvest Performance
- **Metric:** Multi-season spike success
- **Value:** `22.9` `percent`
- **Plan page:** 4
- **Evidence excerpt:** Multi-season spike only success was 22.9%.
- **Codex use:** context_feature / `harvest_context`.
- **Do not:** No direct p_draw or quota override.
- **Suggestion:** Keep source lineage and display value.

### ELK_MULTI_SEASON_SUCCESS_ANY_BULL
- **Topic:** Harvest Performance
- **Metric:** Multi-season any bull success
- **Value:** `28.2` `percent`
- **Plan page:** 4
- **Evidence excerpt:** Multi-season any bull success was 28.2%.
- **Codex use:** context_feature / `harvest_context`.
- **Do not:** No direct p_draw or quota override.
- **Suggestion:** Keep source lineage and display value.

### ELK_LE_AGE_MANAGEMENT_CORE
- **Topic:** Limited Entry Management
- **Metric:** Traditional LE units managed by average age of harvested bulls
- **Value:** `true` `policy`
- **Plan page:** 4
- **Evidence excerpt:** Traditional limited entry units are managed for average age of harvested bulls.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Keep source lineage and display value.

### ELK_ANTLER_GROWTH_96_BY_6_5
- **Topic:** Biological Basis
- **Metric:** Average antler growth achieved by age 6.5
- **Value:** `96` `percent`
- **Plan page:** 4
- **Evidence excerpt:** Most bulls achieved 96% of antler growth potential by 6.5 years old.
- **Codex use:** quality_context / `quality_structure_context`.
- **Do not:** Use to explain trophy-age scoring logic, not raw age truth.
- **Suggestion:** Use to interpret observed age metrics; do not treat as observed age.

### ELK_MAINBEAM_97_BY_6_5
- **Topic:** Biological Basis
- **Metric:** Main beam length achieved by age 6.5
- **Value:** `97` `percent`
- **Plan page:** 4
- **Evidence excerpt:** 97% of main beam length achieved by 6.5 years old.
- **Codex use:** quality_context / `quality_structure_context`.
- **Do not:** Use to explain trophy-age scoring logic, not raw age truth.
- **Suggestion:** Use to interpret observed age metrics; do not treat as observed age.

### ELK_ANTLER_PLATEAU_AFTER_8_5
- **Topic:** Biological Basis
- **Metric:** Main beam length increase after age 8.5
- **Value:** `no increase` `trend`
- **Plan page:** 4
- **Evidence excerpt:** Length does not increase after an elk reaches 8.5 years old.
- **Codex use:** quality_context / `quality_structure_context`.
- **Do not:** Use to explain trophy-age scoring logic, not raw age truth.
- **Suggestion:** Use to interpret observed age metrics; do not treat as observed age.

### ELK_OPPORTUNITY_FROM_LOWERING_AGE_OBJ
- **Topic:** Permit Governance
- **Metric:** Estimated opportunity gain from lowering age objectives by one year
- **Value:** `40-50` `percent`
- **Plan page:** 4
- **Evidence excerpt:** Lowering age objectives by one year can increase opportunity by 40-50%.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Split range into min/max numeric fields where possible.

### ELK_ADULT_COW_SURV_WITH_HARVEST
- **Topic:** Survival Metrics
- **Metric:** Adult female annual survival including harvest
- **Value:** `75-81` `percent`
- **Plan page:** 6
- **Evidence excerpt:** Annual survival ranged from 75 to 81 percent when harvest was included.
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Split range into min/max numeric fields where possible.

### ELK_ADULT_COW_SURV_NO_HARVEST
- **Topic:** Survival Metrics
- **Metric:** Adult female annual survival excluding human harvest
- **Value:** `93-98` `percent`
- **Plan page:** 6
- **Evidence excerpt:** Survival ranged from 93 to 98 percent in absence of harvest by humans.
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Split range into min/max numeric fields where possible.

### ELK_ADULT_MORTALITY_SHARE_HUNTER
- **Topic:** Mortality Drivers
- **Metric:** Share of collared adult females killed by hunters
- **Value:** `over 21` `percent`
- **Plan page:** 6
- **Evidence excerpt:** Over 21 percent of collared elk were killed by hunters.
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Keep source lineage and display value.

### ELK_CALF_SURVIVAL_FIRST_YEAR
- **Topic:** Survival Metrics
- **Metric:** Neonate survival during first year
- **Value:** `41-47` `percent`
- **Plan page:** 6
- **Evidence excerpt:** Neonate survival averaged between 41 and 47 percent.
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Split range into min/max numeric fields where possible.

### ELK_CALF_MORTALITY_COUGAR_SHARE
- **Topic:** Mortality Drivers
- **Metric:** Collared calf first-year mortality attributed to cougars
- **Value:** `up to 45` `percent`
- **Plan page:** 6
- **Evidence excerpt:** Up to 45 percent of collared calves were killed by cougars.
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Keep source lineage and display value.

### ELK_PREGNANCY_RATE_AVG
- **Topic:** Reproduction Metrics
- **Metric:** Average adult pregnancy rate
- **Value:** `85` `percent`
- **Plan page:** 6
- **Evidence excerpt:** Average adult pregnancy rates have been 85%.
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Keep source lineage and display value.

### ELK_PREGNANCY_RATE_RANGE
- **Topic:** Reproduction Metrics
- **Metric:** Adult pregnancy rate range
- **Value:** `55-100` `percent`
- **Plan page:** 6
- **Evidence excerpt:** Pregnancy ranged from 55% to 100%.
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Split range into min/max numeric fields where possible.

### ELK_PRIVATE_LANDS_ONLY_ANTLERLESS_2016
- **Topic:** Distribution Management
- **Metric:** Private-lands-only antlerless permit implementation year
- **Value:** `2016` `year`
- **Plan page:** 8
- **Evidence excerpt:** Division began allowing purchase of private-lands-only antlerless elk permit in 2016.
- **Codex use:** context_feature / `population_context`.
- **Do not:** Do not use as hunt-code harvest truth.
- **Suggestion:** Keep source lineage and display value.

### ELK_LE_DEMAND_2022_APPLICANTS_PERMITS
- **Topic:** Demand Pressure
- **Metric:** Limited entry applicants and permits
- **Value:** `75925 applicants for 3117 permits` `applicants and permits`
- **Plan page:** 17
- **Evidence excerpt:** In 2022, 75,925 hunters applied for 3,117 limited entry permits.
- **Codex use:** display_context / `draw_demand_context`.
- **Do not:** Do not treat as modeled odds.
- **Suggestion:** Keep as demand display/context; add numeric ratio fields only if clearly parseable.

### ELK_LE_DRAW_ODDS_2022
- **Topic:** Demand Pressure
- **Metric:** Limited entry draw odds in 2022
- **Value:** `1:19.8 resident; 1:70.5 nonresident` `odds`
- **Plan page:** 17
- **Evidence excerpt:** Resulting in 1:19.8 draw odds for residents and 1:70.5 for nonresidents.
- **Codex use:** display_context / `draw_demand_context`.
- **Do not:** Do not treat as modeled odds.
- **Suggestion:** Keep as demand display/context; add numeric ratio fields only if clearly parseable.

### ELK_ANY_BULL_SELL_OUT_ACCEL
- **Topic:** Demand Pressure
- **Metric:** General season any bull permit sellout acceleration
- **Value:** `2018 sold out in 34 days; 2020 in less than 8 hours; 2022 in less than 6 hours` `time-to-sellout`
- **Plan page:** 17
- **Evidence excerpt:** Any bull permits sold out increasingly quickly from 2018 to 2022.
- **Codex use:** display_context / `draw_demand_context`.
- **Do not:** Do not treat as modeled odds.
- **Suggestion:** Keep as demand display/context; add numeric ratio fields only if clearly parseable.

### ELK_SPIKE_SELL_OUT_2022
- **Topic:** Demand Pressure
- **Metric:** General season spike sellout timing
- **Value:** `9 hours` `time-to-sellout`
- **Plan page:** 17
- **Evidence excerpt:** General season spike bull tags sold out in just nine hours in 2022.
- **Codex use:** display_context / `draw_demand_context`.
- **Do not:** Do not treat as modeled odds.
- **Suggestion:** Keep source lineage and display value.

### ELK_GENERAL_OPPORTUNITY_TARGETS
- **Topic:** General Season Strategy
- **Metric:** Statewide opportunity targets
- **Value:** `15000 spike permits; up to 4500 multi-season sub-quota; up to 15000 early any-bull permits; unlimited late any-bull; unlimited general archery` `permit strategy`
- **Plan page:** 22
- **Evidence excerpt:** General opportunity strategy lists fixed and unlimited permit lanes.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Split range into min/max numeric fields where possible.

### ELK_YOUTH_GENERAL_OPPORTUNITY
- **Topic:** Youth Strategy
- **Metric:** Youth general season opportunity
- **Value:** `unlimited general season youth bull permits on spike and any-bull units; separate limited draw-only youth any-bull hunt` `permit strategy`
- **Plan page:** 22
- **Evidence excerpt:** Unlimited youth bull permits plus limited-quota draw-only youth any-bull hunt.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Keep source lineage and display value.

### ELK_LE_AGE_CATEGORIES
- **Topic:** Limited Entry Strategy
- **Metric:** Traditional LE age objective categories
- **Value:** `6.5-7.0; 6.0-6.5; 5.5-6.0` `years average age of harvest`
- **Plan page:** 22
- **Evidence excerpt:** Maintain 3 categories of age class harvest objectives.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Split range into min/max numeric fields where possible.

### ELK_LE_PERMIT_INCREASE_GATE
- **Topic:** Limited Entry Strategy
- **Metric:** Condition for increasing LE permits while maintaining quality
- **Value:** `any-legal-weapon 3-year average success over 75% and unit meeting/exceeding age objective` `rule threshold`
- **Plan page:** 22
- **Evidence excerpt:** Increase permits when 3-year success exceeds 75% and age objective is met.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Split range into min/max numeric fields where possible.

### ELK_LE_WEAPON_ALLOCATION_STANDARD
- **Topic:** Limited Entry Strategy
- **Metric:** Traditional LE weapon allocation
- **Value:** `25/15/60` `archery/muzzleloader/any legal weapon percent`
- **Plan page:** 23
- **Evidence excerpt:** 25% archery, 15% muzzleloader, 60% any legal weapon.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Split percentage string into named numeric percentage fields.

### ELK_LE_ANY_WEAPON_SEASON_SPLIT
- **Topic:** Limited Entry Strategy
- **Metric:** Any-weapon split when all three seasons exist
- **Value:** `10/30/17 plus 3 multi-season` `early/mid/late any-weapon and multi-season percent`
- **Plan page:** 23
- **Evidence excerpt:** 10% early, 30% mid, 17% late any-weapon and 3% multi-season.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Split percentage string into named numeric percentage fields.

### ELK_PRIMITIVE_WEAPON_SPLIT
- **Topic:** Restricted Weapons Strategy
- **Metric:** Primitive weapon LE allocation
- **Value:** `50/50` `September archery versus HAMS/restricted weapon percent`
- **Plan page:** 23
- **Evidence excerpt:** Allocate permits 50% September archery and 50% HAMS/restricted weapon.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Split percentage string into named numeric percentage fields.

### ELK_ADAPTIVE_OPPORTUNITY_PERMIT_RULE
- **Topic:** Adaptive Opportunity Hunts
- **Metric:** Late-season adaptive permit sizing rule
- **Value:** `1% of combined LE permits or minimum 5 permits` `permit rule`
- **Plan page:** 23
- **Evidence excerpt:** Permits should equal 1% of combined LE permits or a minimum of 5.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Keep source lineage and display value.

### ELK_HIGH_BULL_COW_TRIGGER_RESTRICTED
- **Topic:** Adaptive Opportunity Hunts
- **Metric:** Restricted/HAMS recommendation trigger
- **Value:** `bull:cow ratio greater than 40 bulls per 100 cows` `ratio threshold`
- **Plan page:** 23
- **Evidence excerpt:** Recommend additional restricted/HAMS hunts on units with bull:cow ratio > 40/100.
- **Codex use:** policy_context / `permit_policy`.
- **Do not:** Use only as governance/validation context.
- **Suggestion:** Keep as demand display/context; add numeric ratio fields only if clearly parseable.

### ELK_HABITAT_FORAGE_TREATMENT_TARGET
- **Topic:** Habitat Management
- **Metric:** Annual forage treatment target
- **Value:** `minimum 40000` `acres per year`
- **Plan page:** 21
- **Evidence excerpt:** Increase forage production by annually treating a minimum of 40,000 acres.
- **Codex use:** context_feature / `habitat_context`.
- **Do not:** Long-horizon context only.
- **Suggestion:** Keep source lineage and display value.

### ELK_HABITAT_MITIGATION_RATIO
- **Topic:** Habitat Management
- **Metric:** Voluntary mitigation ratio for disturbance in crucial habitat
- **Value:** `4:1` `acres improved or conserved per acre disturbed`
- **Plan page:** 21
- **Evidence excerpt:** Voluntary mitigation recommended at a 4:1 ratio.
- **Codex use:** context_feature / `habitat_context`.
- **Do not:** Long-horizon context only.
- **Suggestion:** Keep as demand display/context; add numeric ratio fields only if clearly parseable.

### ELK_INTERNAL_USAGE_RULE
- **Topic:** Data Governance
- **Metric:** Age metrics policy boundary
- **Value:** `Use age metrics for quality context only; do not directly override permit quotas or p_draw` `rule`
- **Plan page:** derived
- **Evidence excerpt:** Implementation guardrail consistent with plan-governance usage.
- **Codex use:** hard_rule / `governance_rule`.
- **Do not:** Must be enforced.
- **Suggestion:** Enforce as hard guardrail.

## Usage Rules

- Use this file for recurring policy and management context.
- Do not use it to overwrite canonical permit truth in `DATABASE.csv`.
- Do not convert policy values directly to `p_draw` without explicit model validation.
- Use observed age data from annual report age tables for actual `average_harvest_age`.
- Use elk plan age objective categories to interpret quality, not to fabricate observations.
- Keep plan-derived rows out of runtime prediction outputs unless a script explicitly labels them `policy_context`.

## Suggested Files Codex Should Build Next

```text
processed_data/elk_plan_context_normalized.csv
processed_data/elk_plan_quality_rules.json
processed_data/elk_age_objective_validation_report.csv
processed_data/elk_age_objective_validation_report.json
```

## Suggested Tests Codex Should Add

```text
test_elk_plan_does_not_override_database_permits
test_elk_plan_does_not_override_p_draw
test_elk_age_objective_not_used_as_observed_age
test_elk_age_quality_uses_observed_harvest_age_when_available
test_elk_le_permit_gate_is_validation_only
```
