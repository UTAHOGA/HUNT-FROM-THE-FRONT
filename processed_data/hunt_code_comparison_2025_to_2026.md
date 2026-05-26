# Hunt Code Comparison 2025 To 2026

Read-only comparison of source-lined 2025 historical permit codes to current 2026 DATABASE hunt codes.

## Summary

- 2026 DATABASE universe: `1411`
- 2025 historical permit codes: `1028`
- 2026 populated permit codes: `1261`
- Exact same-code continuity: `1027`
- 2025 codes absent from 2026 DATABASE: `0`
- 2025 codes without populated 2026 permits: `1`
- 2026 populated codes without exact 2025 code: `234`
- 2026 populated codes with mapped 2025 history: `133`
- 2026 populated codes with no mapped 2025 history: `101`
- 2026 reference-only rows without 2025/2026 permits: `149`

## Guardrail

This is a read-only hunt-code comparison. Source-lined 2025 historical permit codes are canonical passed-year truth, and populated 2026 permit codes are current DWR Hunt Planner truth. Exact-code gaps must be checked against the promoted current-to-historical crosswalk before being treated as truly new. Only promoted historical_hunt_code mappings are used for continuity; candidate/name-match fields remain review evidence.

## Status Counts

- `CURRENT_2026_CODE_WITH_MAPPED_2025_HISTORY`: `133`
- `CURRENT_2026_PERMIT_CODE_NO_2025_HISTORY`: `101`
- `CURRENT_2026_REFERENCE_ONLY_NO_2025_OR_2026_PERMITS`: `149`
- `EXACT_SAME_CODE_2025_AND_2026_PERMITTED`: `1027`
- `HISTORICAL_2025_CODE_PRESENT_BUT_NO_2026_PERMIT_VALUE`: `1`

## Review Priority Counts

- `HIGH`: `1`
- `LOW`: `149`
- `MEDIUM`: `234`
- `NONE`: `1027`
