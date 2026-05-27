import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate-remaining-2025-history-crosswalk-boundaries.py"
SUMMARY = (
    ROOT
    / "data_truth/comparison_outputs/validation/"
    / "remaining_2025_history_crosswalk_boundary_closeout_summary.json"
)


def run_script():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_remaining_history_crosswalk_boundary_closeout_has_no_blockers():
    run_script()
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["blocker_count"] == 0
    assert summary["database_row_count"] == 1449
    assert summary["database_unique_hunt_code_count"] == 1449
    assert summary["broad_2025_draw_source_rows"] == 874
    assert summary["broad_2025_source_codes_missing_database_count"] == 0
    assert summary["broad_2025_safe_blank_candidate_count"] == 0
    assert summary["dropped_split_crosswalk_review_count"] == 13
    assert summary["dropped_split_crosswalk_blocker_count"] == 0
    assert summary["official_boundary_mismatch_count"] == 0
    assert summary["expo_hard_copy_missing_database_count"] == 0
    assert summary["conservation_lock_missing_database_count"] == 0


def test_remaining_crosswalk_rows_are_reviewed_not_forced_remaps():
    run_script()
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    statuses = summary["dropped_split_review_status_counts"]

    assert statuses == {
        "REVIEWED_HISTORICAL_ONLY_NO_DEFINITE_2026_ONE_TO_ONE_MATCH": 13,
    }
