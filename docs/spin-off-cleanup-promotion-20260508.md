# Spin-Off Cleanup Promotion Audit (2026-05-08)

## Scope
- `pipeline/RAW/hunt_unit_database/spin_off_cleanup_phase2_20260508`
- `_exports/spin_off_cleanup_20260508`
- `_exports/spin_off_cleanup_phase2_20260508`

## Folder Inventory Summary
- `pipeline/RAW/hunt_unit_database/spin_off_cleanup_phase2_20260508`
  - 47 files total
  - Primary content: `canonical/`, `data/`, `lib/`, `schemas/`, `docs/`, `generated/`
- `_exports/spin_off_cleanup_20260508`
  - 2061 files total
  - Primary content: `pages-dist` snapshots, bulk `processed_data` backups, server-pull outputs, reports
- `_exports/spin_off_cleanup_phase2_20260508`
  - 47 files total (mirror of phase2 payload)

## Comparison Against Root
For `spin_off_cleanup_phase2_20260508` vs repo root by matching relative paths:
- Identical: 40
- Different: 4
- Missing in root: 3

Different files:
- `canonical/permit-allocation-2026-integrity-report.json`
- `generated/pages/hard-copies.json`
- `generated/pages/hunt-planner.json`
- `generated/pages/hunt-research.json`

Missing-in-root files:
- `data/hunt-master-canonical-2026-foundation.backup_before_add_106_missing_20260507_214651.csv`
- `data/hunt-master-canonical-2026-foundation.with_106_missing_added_20260507_214729.csv`
- `_moved_paths.txt`

Interpretation:
- The 4 differing root files are newer runtime/regenerated outputs and were kept as root authority.
- The 3 missing files are backup/helper artifacts, not required runtime files.

## Promotion Decision
Promoted from spin-off packages into root runtime paths:
- None required (runtime/source files were already integrated or newer in root).

Ignored as temporary/debug/archive:
- All of `_exports/spin_off_cleanup_20260508` (pages-dist snapshots, backup trees, debug/report payloads)
- Backup-only phase2 files listed above

## Validation and Build Results
Executed successfully:
- `npm run sync:permits-2026`
- `npm run verify:permits-2026`
- `npm run validate:canonical`
- `npm run compare:runtime-contracts`
- `npm run promotion:safety`
- `npm run test`
- `npm run build`

Key outcomes:
- Canonical validates with hunt catalog count `1394`
- Permit-allocation sync/verify reports `0` mismatches after sync
- Runtime contract compare: no findings
- Promotion safety: no blockers

Warnings (non-blocking):
- Some hard-copy manifest entries reference PDFs not present in local filesystem paths.

## GitHub Pages Main/Root Readiness
- Root runtime files are authoritative.
- This cleanup did **not** rely on `pages-dist` for deployment behavior.
- Main/root deployment will use updated tracked root files.
