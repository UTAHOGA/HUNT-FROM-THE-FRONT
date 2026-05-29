# Outfitter Data Readiness Report

Generated: 2026-05-29T17:09:54.090Z

- Public feed rows: 0
- Internal feed rows: 11
- Audited records: 11

## Readiness Status Counts

- HOLD_INTERNAL_ONLY: 11

## Main Recommendations

- Promote no outfitter publicly until reviewed_at and source_evidence_count fields exist.
- Add explicit service_types instead of relying on inferred services.
- Add unit coverage keyed to hunt codes or reviewed boundary IDs before matching becomes public-facing.
- Keep internal-only records out of `outfitters-public.json` until contact, service, unit, and review fields are complete.

