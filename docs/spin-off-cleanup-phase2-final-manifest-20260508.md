# Spin-Off Cleanup Phase 2 Final Manifest (2026-05-08)

Source folder: `pipeline/RAW/hunt_unit_database/spin_off_cleanup_phase2_20260508`

## Summary
- Total files: 47
- Promoted identical: 43
- Promoted but updated in active repo: 
- Not promoted: 3
- Scripts: 8
- Data files: 32
- Report/note files: 7

## Not Promoted (Intentional)
- _moved_paths.txt: one-time move helper artifact; superseded by final manifest report
- data\hunt-master-canonical-2026-foundation.backup_before_add_106_missing_20260507_214651.csv: not required by runtime or canonical active paths
- data\hunt-master-canonical-2026-foundation.with_106_missing_added_20260507_214729.csv: not required by runtime or canonical active paths

## Promoted But Updated
- canonical\permit-allocation-2026-integrity-report.json: repo version is newer than spin-off snapshot

## Notes
- Active runtime and canonical files are in root tracked locations (`data/`, `processed_data/`, `canonical/`, `generated/`, `docs/`, `schemas/`).
- This manifest preserves auditability of what was in the spin-off folder and how each file resolved.
