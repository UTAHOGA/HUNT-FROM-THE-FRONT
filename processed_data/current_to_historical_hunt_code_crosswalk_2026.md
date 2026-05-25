# Current-to-Historical Hunt Code Crosswalk 2026

This file promotes the older backcheck/crosswalk work into a stable truth artifact.
It is not a runtime rewrite table.

## Validation

- Current target codes: 169
- Output rows: 169
- Missing from DATABASE.csv: 0
- Duplicate current-code rows: 0
- Blockers: 0

## Prefix Counts

- BI: 2
- CG: 1
- DS: 7
- EA: 5
- EB: 2
- EL: 126
- EX: 1
- LD: 6
- LO: 8
- LP: 6
- RS: 5

## Status Counts

- CURRENT_REFERENCE_ONLY_NEEDS_REVIEW: 4
- PROMOTED_EXACT_HISTORY: 19
- PROMOTED_PINNED_CANDIDATE: 8
- PROMOTED_PREFIX_SWAP_CANDIDATE: 138

## Spot Checks

- LD1001: DB1001; PREFIX_SWAP_LD_TO_DB; PROMOTED_PREFIX_SWAP_CANDIDATE (private-land deer prefix crosswalk)
- LP5025: PB5025; PREFIX_SWAP_LP_TO_PB; PROMOTED_PREFIX_SWAP_CANDIDATE (private-land pronghorn prefix crosswalk)
- EL3000: EB3000; PREFIX_SWAP_EL_TO_EB; PROMOTED_PREFIX_SWAP_CANDIDATE (private-land bull elk prefix crosswalk)
- RS1001: RS6701; PINNED_HISTORICAL_PUBLIC_OR_CONSERVATION_CANDIDATE; PROMOTED_PINNED_CANDIDATE (bighorn conservation candidate)
- BI6527: BI6527; EXACT_CODE_HISTORY; PROMOTED_EXACT_HISTORY (exact bison history/reference)
- EX1000: (none); CURRENT_REFERENCE_ONLY; CURRENT_REFERENCE_ONLY_NEEDS_REVIEW (extended archery reference-only)
- CG9999: (none); CURRENT_REFERENCE_ONLY; CURRENT_REFERENCE_ONLY_NEEDS_REVIEW (cougar reference-only)
