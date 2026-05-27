# Database Historical Permit Lineage 2026

This audit verifies that passed-year permit fields in canonical `DATABASE.csv` carry source lineage.

## Summary

- DATABASE rows: `1449`
- Audit rows: `2898`
- Historical years detected: `2025`
- Full 2025 historical permit universe rows: `1085`
- 2025 bonus-point draw subset rows: `682`
- 2025 non-bonus/general subset rows: `403`
- Canonical historical source-truth rows: `1767`
- Lineage blocker count: `0`

## Guardrail

Passed hunt-year permit values are canonical source truth when populated with reviewed source lineage. They must not drift because a newer working file, RAC file, inferred value, or comparison output disagrees. Historical populated values without lineage are blocked for lineage repair. The permits_2025 family is the full 2025 historical permit universe in DATABASE.csv; permits_2025_draw is a narrower bonus-point draw-results subset and must not be described as the full 2025 draw/permit universe.

## Family Status Counts

### permits_2025

- `CANONICAL_HISTORICAL_SOURCE_TRUTH`: `1085`
- `NO_HISTORICAL_VALUE`: `364`

### permits_2025_draw

- `CANONICAL_HISTORICAL_SOURCE_TRUTH`: `682`
- `NO_HISTORICAL_VALUE`: `767`

## Paired Family Compare Counts

- `BOTH_BLANK`: `364`
- `MATCH`: `682`
- `PRIMARY_ONLY`: `403`
