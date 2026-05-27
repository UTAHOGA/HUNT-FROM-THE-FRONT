# Remaining 2025 History, Crosswalk, And Boundary Closeout

- Generated UTC: `2026-05-27T02:09:03+00:00`
- DATABASE rows: `1449`
- Broad 2025 draw-source rows checked: `874`
- Broad 2025 source codes missing DATABASE: `0`
- Broad 2025 safe blank candidates remaining: `0`
- Dropped/split crosswalk rows reviewed: `13`
- Dropped/split crosswalk blockers: `0`
- Official boundary JSON mismatches: `0`
- Expo hard-copy promoted rows checked: `3`
- Conservation lock rows checked: `8`
- Blockers: `0`

## Conclusion

The broad 2025 historical permit universe is complete against the 874-row 2024 draw-results source. The remaining dropped/split rows are reviewed historical-only rows with no definite one-to-one active 2026 match.

## Guardrails

- Closeout audit only; DATABASE.csv is not modified.
- Dropped/split historical codes are not force-mapped unless an exact active 2026 name/species/sex/weapon/boundary match exists.
- permits_2025 is treated as the broad 2025 historical permit universe; permits_2025_draw remains the narrower draw subset.
- Blank DWR quota rows for expo/conservation are preserved when backed by hard-copy or lock-table evidence.
