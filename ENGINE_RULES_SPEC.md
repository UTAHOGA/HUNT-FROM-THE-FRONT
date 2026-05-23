# Engine Rules Spec

## Frontend runtime contract

The Hunt Research page consumes these runtime files:

- `processed_data/draw_reality_engine.csv`
- `processed_data/point_ladder_view.csv`
- `processed_data/hunt_master_enriched.csv`
- `processed_data/hunt_unit_reference_linked.csv`

Rows remain keyed by:

- `hunt_code`
- `residency`
- `points`

## Internal probability units

- `p_*` fields remain decimals in `[0, 1]`.
- `*_pct` fields remain percentages in `[0, 100]`.
- `display_odds_pct` remains a percentage in `[0, 100]`.
- Legacy odds and projection fields remain percentages in `[0, 100]`.

These numeric fields are not renamed by the UI.

## Draw-odds selection order

Whenever the Hunt Research UI needs a user-facing draw-odds value, it selects the first numeric source in this order:

1. `display_odds_pct`
2. `p_draw_mean * 100`
3. `odds_2026_projected`
4. `max_pool_projection_2026`
5. `random_draw_odds_2026`
6. `random_draw_projection_2026`
7. otherwise `Not available`

The UI does not select draw odds from `status`.

## Draw-odds display format

All user-facing draw odds are displayed in combined format:

- `~1 in X or Y%`

Examples:

- `100% -> ~1 in 1 or 100%`
- `50% -> ~1 in 2 or 50%`
- `42% -> ~1 in 2.4 or 42%`
- `25% -> ~1 in 4 or 25%`
- `10% -> ~1 in 10 or 10%`
- `1% -> ~1 in 100 or 1%`
- `0% -> No modeled chance`
- missing numeric odds -> `Not available`

Percentage-only display for draw odds is superseded.

This applies to:

- the primary odds card
- the ladder/table odds cells
- the source snapshot/modal draw-odds boxes
- any other draw-odds UI text emitted from Hunt Research

It does not change harvest percentages, permit-change percentages, progress bars, or unrelated percentages.

## MAX POOL rule

`status = MAX POOL` is descriptive only.

It must not, by itself, create:

- `~1 in 1 or 100%`
- a guaranteed badge
- a green light

A MAX POOL row may display `~1 in 1 or 100%` only when:

- the selected numeric odds field is actually `100%`, or
- `guaranteed_probability >= 0.999`

The older shortcut that forced MAX POOL rows to `100%` is removed and superseded.

## Verdict and signal rules

- Verdict badges and recommendation text must be driven by numeric modeled or legacy odds fields plus guarantee fields, not by `status` alone.
- The green signal is appropriate only for effectively guaranteed rows.
- Yellow indicates a live modeled chance where pressure still matters.
- Red indicates low, random-only, or unavailable modeled chance.

## Materialization note

Optional display-only fields such as `display_odds_one_in_or_pct` may be added in the future, but:

- `display_odds_pct` stays numeric
- internal probability math does not change
- display formatting remains a UI concern unless an explicit materialized display field is added

## Point ladder max-point and random-pool rules

The ladder separates historical DWR results from next-year predictions:

- `2025 Draw Results` shows the official historical point-row result only when DWR awarded a permit at that point level.
- DWR `N/A` with `total_permits = 0` renders as a blank ladder cell, not `Not available`.
- `2026 Max Point Pool` is populated only from the recomputed rolled-forward max-point pool.
- `2026 Random Draw` is populated from the prediction engine's modeled random-pool probability, not from a same-point historical success ratio.

For bonus-point hunts, the prediction engine rolls the applicant stack forward
before allocating the current quota. Successful max-point and random-pool
applicants are removed; unsuccessful applicants advance by one point with
retention/reapply assumptions; lower-point additions are estimated from observed
transitions.

Rows fully cleared by max-point permits are `max_pool_guaranteed`. The cutoff
row where remaining max-point permits are fewer than applicants at that level is
`max_pool_cutoff_mixed`. Rows below that are `random_pool`.
