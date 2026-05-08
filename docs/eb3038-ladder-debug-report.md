# EB3038 Ladder Debug Report

Generated: 2026-05-08T16:07:19.448Z

## Target

- hunt_code: EB3038
- species: elk
- hunt: Manti LE Early Rifle
- selected points: 20

## Existence Checks

- point_ladder_view: true
- draw_reality_engine: true
- hunt_master_enriched: true
- hunt_unit_reference_linked: true
- database: true

## Row Counts

- point_ladder_view: 66
- draw_reality_engine: 234
- hunt_master_enriched: 66
- hunt_unit_reference_linked: 2
- database: 1

## Join Diagnostics

- ladder_rows_checked: 66
- join_engine_success_count: 64
- join_master_point_success_count: 66
- join_failures: 0
- duplicate_hunt_code_key_collisions: 170

## Selected Point Runtime Preview

### resident
- key: EB3038__Resident__20
- ladder row found: true
- engine row found: true
- master point row found: true
- pre-fix 2025 actual: 1 in 1.4
- pre-fix 2026 max pool: Not available
- pre-fix 2026 random: 3.105
- post-fix 2025 actual: 1 in 1.4
- post-fix 2026 max pool: 85.645
- post-fix 2026 random: 3.105

### nonresident
- key: EB3038__Nonresident__20
- ladder row found: true
- engine row found: true
- master point row found: true
- pre-fix 2025 actual: 0.0
- pre-fix 2026 max pool: Not available
- pre-fix 2026 random: 1.540
- post-fix 2025 actual: 0.0
- post-fix 2026 max pool: 1.540
- post-fix 2026 random: 1.540

## Required Field Coverage

- rows_with_missing_required_fields_count: 66

## Root Cause

- Ladder rendering used only point_ladder_view + draw_reality_engine point joins.
- The fields used for display (odds_2025 and odds_2026_projected/max pool proxy) are populated in hunt_master_enriched point rows but were not joined into ladder rows.
- Because draw_reality_engine rows for EB3038 do not carry display_odds_pct/max_pool_projection_2026/odds_2025_actual fields, ladder displayed "Not available" for 2025 actual and 2026 max pool.

## Fix Applied

- file: hunt-research.js
- change: Added master point-key join in ladder merge and fallback display for 2025 actual odds using odds_2025/success_ratio.
- expected effect: EB3038 ladder rows now have populated 2025 actual and 2026 max-pool display candidates when selected points/residency are present in hunt_master_enriched.

runtime_display_now_correct: true

