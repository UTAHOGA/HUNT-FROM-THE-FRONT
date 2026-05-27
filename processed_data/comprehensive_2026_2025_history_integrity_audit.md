# Comprehensive 2026/2025 History Integrity Audit

- Generated UTC: `2026-05-27T00:09:02+00:00`
- DATABASE active rows: `1449`
- DATABASE unique hunt codes: `1449`
- Retired current-code ledger rows: `17`
- Fatal blockers: `0`
- Review warnings: `1`

## Clean Core Checks

- Active DATABASE has no duplicate hunt codes and no blank boundary IDs.
- Retired 2026 current codes are absent from active DATABASE and preserved in the ledger.
- Live-online DATABASE missing-code count is zero in the latest committed DWR snapshot audit.
- Active EA reconciliation is clean: 204 live/current active EA rows and 204 DATABASE EA rows.
- Permit overlay validations show zero numeric mismatches against protected DATABASE cells.

## Remaining Review Classes

- `harvest_2025_for_2026_database_code_presence`: `4` issue rows. active_database_matches=1114; unmatched_active_database=4; retired_matches=0. Next: Resolve remaining unmatched harvest codes as historical-only, CWMU-retired, or current-code crosswalk candidates.

## Output Files

- Dashboard CSV: `data_truth/comparison_outputs/validation/comprehensive_2026_2025_history_integrity_audit.csv`
- Open issues CSV: `data_truth/comparison_outputs/validation/comprehensive_2026_2025_history_integrity_open_issues.csv`
- Summary JSON: `data_truth/comparison_outputs/validation/comprehensive_2026_2025_history_integrity_summary.json`

Guardrail: this audit does not alter website feeds, materializer outputs, or protected numeric DATABASE cells.
