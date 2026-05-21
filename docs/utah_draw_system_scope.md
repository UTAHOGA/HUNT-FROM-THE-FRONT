# Utah Draw System Scope

## Target Scope

The approved predictive-engine universe is limited to:

- Big game
- Turkey
- Bear
- Mountain lion / cougar

Target-scope big-game families include:

- Deer
- Elk
- Pronghorn
- Moose
- Bison
- Bighorn sheep
- Mountain goat
- Antlerless deer
- Antlerless elk
- Doe pronghorn
- Antlerless moose
- Ewe bighorn sheep
- CWMU public big-game permits where present
- Limited-entry big game
- Premium limited-entry big game
- Once-in-a-lifetime big game
- General-season big-game draw categories
- Dedicated Hunter deer where present
- Youth big-game draw categories where present
- Landowner big-game categories where present
- Mitigation / depredation big-game categories where present
- Remaining-permit big-game categories where present
- Private-lands-only antlerless elk where present

## Out Of Scope

These categories must be classified as `OUT_OF_SCOPE_NON_TARGET` when they appear:

- Swan
- Sandhill crane
- Grouse
- Waterfowl
- Upland game other than turkey
- Small game
- Fishing
- Other non-target wildlife categories

## Classifier Values

- `BONUS_OIL_BIG_GAME`
- `BONUS_LE_BIG_GAME`
- `BONUS_PLE_BIG_GAME`
- `BONUS_CWMU_BIG_GAME`
- `BONUS_ANTLERLESS_MOOSE`
- `BONUS_EWE_BIGHORN`
- `BONUS_TURKEY`
- `SPORTSMAN_PERMIT`
- `PREFERENCE_GENERAL_SEASON_BUCK_DEER`
- `PREFERENCE_DEDICATED_HUNTER_DEER`
- `PREFERENCE_ANTLERLESS_DEER`
- `PREFERENCE_ANTLERLESS_ELK`
- `PREFERENCE_DOE_PRONGHORN`
- `GENERAL_BIG_GAME_OTHER`
- `BEAR_DRAW`
- `MOUNTAIN_LION_DRAW`
- `PRIVATE_LANDS_ONLY_ANTLERLESS_ELK`
- `RANDOM_ONLY_TARGET`
- `OTC_OR_REMAINING_TARGET`
- `LANDOWNER_BIG_GAME`
- `MITIGATION_OR_DEPREDATION_BIG_GAME`
- `UNKNOWN_TARGET`
- `OUT_OF_SCOPE_NON_TARGET`

## Algorithm Status Values

- `MODELED_BONUS`
- `MODELED_PREFERENCE`
- `MODELED_ALLOCATION`
- `MODELED_AVAILABILITY`
- `MODELED_RANDOM_ONLY`
- `IN_SCOPE_MODEL_PENDING`
- `EXCLUDED_NOT_PREDICTIVE_DRAW`
- `OUT_OF_SCOPE_NON_TARGET`
- `UNKNOWN_TARGET_NEEDS_REVIEW`

## Current Bonus Engine Usage

The accepted production predictive engine currently models:

- `BONUS_OIL_BIG_GAME`
- `BONUS_LE_BIG_GAME`
- `BONUS_PLE_BIG_GAME`

Preserved behavior:

- One permit by hunt/residency goes to the random/regular side, not max-point.
- `7` permits split `4 max / 3 random`.
- `9` permits split `5 max / 4 random`.
- EB3024 regression remains required.
- `MAX POOL` is descriptive only and must not force `100%`.
- UI odds precedence remains:
  1. `p_draw_pct`
  2. `p_draw`
  3. `p_bonus_pool_pct / p_random_pool_pct`
  4. legacy fallback
  5. `Not available`

## Categories Requiring Preference Or Other Strategy

These categories must not use the OIL/LE/PLE bonus algorithm:

- `PREFERENCE_GENERAL_SEASON_BUCK_DEER`
- `PREFERENCE_DEDICATED_HUNTER_DEER`
- `PREFERENCE_ANTLERLESS_DEER`
- `PREFERENCE_ANTLERLESS_ELK`
- `PREFERENCE_DOE_PRONGHORN`
- `BEAR_DRAW`
- `MOUNTAIN_LION_DRAW`
- `PRIVATE_LANDS_ONLY_ANTLERLESS_ELK`

Reason:

- General-season deer and antlerless deer/elk/doe pronghorn are preference-point systems, not OIL/LE/PLE bonus systems.
- Mountain lion/cougar uses a rule-status and availability strategy for 2026, not a draw-odds model.

## Current State

Completed:

- Phase 1: OIL / LE / PLE bonus engine
- Phase 2: target-scope classifier and guardrails
- Phase 3: general-season buck deer preference engine
- Phase 4: antlerless deer / antlerless elk / doe pronghorn preference engine
- Phase 5: Dedicated Hunter deer preference engine
- Phase 6: CWMU public + antlerless moose + ewe bighorn bonus families
- Phase 7: limited-entry turkey bonus strategy
- Phase 8: public bear bonus strategy + Sportsman permit classifier
- Phase 9: private-lands-only antlerless elk allocation / availability strategy
- Phase 10: mountain lion / cougar rule-status + availability strategy
- Phase 11: Sportsman permit odds strategy
- Phase 12: bear subtype-aware quota draw + availability strategy
- Phase 13: mountain lion / cougar rule-status + availability closeout
- Phase 14: private-lands-only antlerless elk allocation / availability closeout

Currently modeled as `MODELED_BONUS`:

- `BONUS_OIL_BIG_GAME`
- `BONUS_LE_BIG_GAME`
- `BONUS_PLE_BIG_GAME`
- `BONUS_CWMU_BIG_GAME`
- `BONUS_ANTLERLESS_MOOSE`
- `BONUS_EWE_BIGHORN`
- `BONUS_TURKEY`
- `BEAR_DRAW`

Currently modeled as `MODELED_PREFERENCE`:

- `PREFERENCE_GENERAL_SEASON_BUCK_DEER`
- `PREFERENCE_ANTLERLESS_DEER`
- `PREFERENCE_ANTLERLESS_ELK`
- `PREFERENCE_DOE_PRONGHORN`
- `PREFERENCE_DEDICATED_HUNTER_DEER`

Currently modeled as `MODELED_ALLOCATION`:

- `PRIVATE_LANDS_ONLY_ANTLERLESS_ELK`

Currently modeled as `MODELED_AVAILABILITY`:

- `MOUNTAIN_LION_DRAW`

Currently modeled as `MODELED_SPORTSMAN_DRAW`:

- `SPORTSMAN_PERMIT`

Still pending:

- `YOUTH_GENERAL_DEER`
- `YOUTH_GENERAL_ANY_BULL_ELK`
- `GENERAL_BIG_GAME_OTHER`
- `RANDOM_ONLY_TARGET`
- `OTC_OR_REMAINING_TARGET`
- `LANDOWNER_BIG_GAME`
- `MITIGATION_OR_DEPREDATION_BIG_GAME`

Private-lands-only antlerless elk note:

- This category stays in scope.
- It is modeled as an allocation / availability family, not a preference-draw probability model.
- Phase 14 closes this family as an allocation-status strategy with explicit availability semantics when source support exists.
- It must not receive `p_draw`, `p_draw_pct`, `p_bonus_pool`, `p_random_pool`, or `p_preference_draw`.
- Allocation fields such as `permits_allotted`, `allocation_status`, `p_availability`, and `availability_pct` populate only when source data supports them.

Sportsman permit note:

- Sportsman permits are classified as their own statewide draw family.
- They are modeled from the official Sportsman odds source, not from hunt-code suffix rules.
- They do not use bonus pools, preference points, max-point pools, or bear-availability logic.
- `BR1000`, `DB0007`, `RS0001`, and `TK0001` are all Sportsman permits even though not every Sportsman code ends with `1000`.

Bear note:

- `BR1000` remains `SPORTSMAN_PERMIT`, not `BEAR_DRAW`.
- Harvest objective and pursuit-only bear rows are surfaced as availability/rule-status rows, not draw odds.
- Only true limited-entry bear hunts remain in the bear bonus-draw path.

Mountain lion / cougar note:

- Utah cougar hunting is treated as statewide OTC rule-status and availability, not draw odds.
- The local geometry source lists management/reporting units used for check-in and harvest reporting.
- Phase 13 closes this family as an availability strategy with explicit rule-status reporting, not a draw-odds strategy.
- `MOUNTAIN_LION_DRAW` rows must not receive `p_draw`, `p_draw_pct`, `p_bonus_pool`, `p_random_pool`, or `p_preference_draw`.
- Availability fields such as `permit_availability_type`, `season_start`, `season_end`, `unit_name`, `unit_status`, `p_availability`, and `availability_pct` are the user-facing outputs for this family.

Out of scope:

- swan
- crane
- grouse
- waterfowl
- small game
- fishing
- non-turkey upland game
- other non-target wildlife categories
