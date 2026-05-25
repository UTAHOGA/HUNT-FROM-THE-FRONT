# Database Authoritative Permit Overlay Plan 2026

This is a reviewable action queue. It does not modify `DATABASE.csv` or runtime files.

## Summary

- Output rows: `1412`
- Unique hunt codes: `1412`
- Database numeric protected rows: `1261`
- Target-only blocker codes: `1`

## Guardrail

Populated numeric 2026 permit/allotment cells in canonical DATABASE.csv are direct Utah DWR Hunt Planner truth. Populated 2025 or older permit fields are historical evidence fields unless separately sourced as current Hunt Planner data. This plan only directs derived outputs to use DATABASE values where populated; it does not modify DATABASE.csv or promote comparison-source values over DATABASE.csv.

## Action Counts

- `ADD_DATABASE_CODE_TO_DERIVED_UNIVERSE`: `123`
- `BLOCK_TARGET_CODE_NOT_IN_DATABASE`: `1`
- `NO_ACTION_DATABASE_MATCH`: `688`
- `NO_NUMERIC_PERMIT_DATA`: `140`
- `REVIEW_TARGET_ONLY_2026_VALUE`: `5`
- `USE_DATABASE_2026_PERMITS_IN_DERIVED_OUTPUTS`: `455`

## Review Priority Counts

- `HIGH`: `579`
- `MEDIUM`: `5`
- `NONE`: `828`

## Row Origin Counts

- `DATABASE_ONLY`: `123`
- `TARGET_AND_DATABASE`: `1288`
- `TARGET_ONLY`: `1`
