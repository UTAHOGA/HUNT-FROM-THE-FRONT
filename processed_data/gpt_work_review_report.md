# GPT Work Review Report

## Executive Summary

- Active repo: `C:\Users\tyler\Desktop\GitHub\HUNTS`
- Forecast year: `2026`
- Source years: `2021, 2022, 2023, 2024, 2025`
- Tests passed: `111`
- Tests failed: `0`
- Youth general deer was separated into its own in-scope family and left pending rather than being merged into adult general deer without proof.
- Youth general any-bull elk was separated into its own in-scope family and left pending rather than being forced into bonus or adult logic.

## Phase Status

| Phase | Status |
|---|---|
| Youth general deer / youth any-bull elk | implemented as separated in-scope pending families |

## Row Counts

| Metric | Count |
|---|---:|
| Total predictive rows | 27767 |
| MODELED_BONUS | 25233 |
| MODELED_PREFERENCE | 1731 |
| MODELED_ALLOCATION | 54 |
| MODELED_AVAILABILITY | 139 |
| MODELED_SPORTSMAN_DRAW | 10 |
| IN_SCOPE_MODEL_PENDING | 398 |
| EXCLUDED_NOT_PREDICTIVE_DRAW | 4 |
| OUT_OF_SCOPE_NON_TARGET | 198 |

## Youth Summary

| Metric | Count |
|---|---:|
| Total youth rows reviewed | 4927 |
| Youth general deer rows reviewed | 4853 |
| Youth general deer active predictive rows | 0 |
| Youth general deer active predictive hunt codes | 0 |
| Youth general any-bull elk rows reviewed | 74 |
| Youth general any-bull elk active predictive rows | 4 |
| Youth general any-bull elk active predictive hunt codes | 2 |
| Youth rows with p_draw | 0 |
| Youth rows with p_draw_pct | 0 |
| Youth rows with p_preference_draw | 0 |
| Youth rows with p_bonus_pool | 0 |
| Youth rows with p_random_pool | 0 |
| Duplicate key count | 0 |

## Guardrails

- Duplicate key count remains `0`.
- Pending rows with `p_draw`: `0`.
- Out-of-scope rows with `p_draw`: `0`.
- Bear Phase 12 guardrails: pass.
- Turkey alignment: pass.
- Private-lands-only antlerless elk separation: pass.
- Mountain lion / cougar behavior unchanged: pass.
- Preference field contract: pass.
- EB3024: pass.
- One-permit random-only: pass.
- MAX POOL safety: pass.
- UI precedence: pass.

## Unresolved Issues

- Youth general deer remains in scope but active 2026 source support is still ambiguous because the current deer permit surface does not cleanly prove a distinct youth-only predictive pool.
- Youth general any-bull elk is separated correctly, but current source support still does not justify odds or allocation probability publication, so the active predictive rows remain model-pending.

## Recommended Next Step

Choose the next remaining pending family instead of forcing youth rows into unsupported draw math.
