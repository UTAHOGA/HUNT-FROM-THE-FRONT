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
- Bear and mountain lion/cougar remain target-scope, but this repo does not yet contain an accepted production predictive strategy audit proving they match the current big-game bonus model.

## Current State

Currently modeled:

- `BONUS_OIL_BIG_GAME`
- `BONUS_LE_BIG_GAME`
- `BONUS_PLE_BIG_GAME`

Currently in scope and model pending:

- `BONUS_CWMU_BIG_GAME`
- `BONUS_ANTLERLESS_MOOSE`
- `BONUS_EWE_BIGHORN`
- `BONUS_TURKEY`
- `PREFERENCE_GENERAL_SEASON_BUCK_DEER`
- `PREFERENCE_DEDICATED_HUNTER_DEER`
- `PREFERENCE_ANTLERLESS_DEER`
- `PREFERENCE_ANTLERLESS_ELK`
- `PREFERENCE_DOE_PRONGHORN`
- `GENERAL_BIG_GAME_OTHER`
- `BEAR_DRAW`
- `MOUNTAIN_LION_DRAW`
- `PRIVATE_LANDS_ONLY_ANTLERLESS_ELK`

Excluded from predictive draw modeling:

- `RANDOM_ONLY_TARGET`
- `OTC_OR_REMAINING_TARGET`
- `LANDOWNER_BIG_GAME`
- `MITIGATION_OR_DEPREDATION_BIG_GAME`

Private-lands-only antlerless elk note:

- This category stays in scope.
- It should be promoted to an allocation / availability strategy, not a preference-draw probability model.
- Until that strategy exists, it remains `IN_SCOPE_MODEL_PENDING` and must not receive fake `p_draw` values.

Out of scope:

- `OUT_OF_SCOPE_NON_TARGET`
