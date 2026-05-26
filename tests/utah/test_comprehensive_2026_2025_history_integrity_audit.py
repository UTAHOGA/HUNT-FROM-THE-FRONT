from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit-comprehensive-2026-2025-history-integrity.py"
DASHBOARD = ROOT / "data_truth" / "comparison_outputs" / "validation" / "comprehensive_2026_2025_history_integrity_audit.csv"
OPEN_ISSUES = ROOT / "data_truth" / "comparison_outputs" / "validation" / "comprehensive_2026_2025_history_integrity_open_issues.csv"
SUMMARY = ROOT / "data_truth" / "comparison_outputs" / "validation" / "comprehensive_2026_2025_history_integrity_summary.json"
REPORT = ROOT / "processed_data" / "comprehensive_2026_2025_history_integrity_audit.md"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def run_audit() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_comprehensive_integrity_audit_outputs_expected_core_counts() -> None:
    run_audit()

    assert DASHBOARD.exists()
    assert OPEN_ISSUES.exists()
    assert SUMMARY.exists()
    assert REPORT.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["fatal_blocker_count"] == 0
    assert summary["database"]["row_count"] == 1394
    assert summary["database"]["unique_hunt_code_count"] == 1394
    assert summary["database"]["duplicate_hunt_code_count"] == 0
    assert summary["database"]["blank_boundary_id_count"] == 0
    assert summary["retired_current_codes"]["ledger_row_count"] == 17
    assert summary["retired_current_codes"]["retired_codes_still_active_count"] == 0
    assert summary["permit_overlay_numeric_issue_total"] == 0


def test_comprehensive_integrity_audit_tracks_known_review_queue() -> None:
    run_audit()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["review_warning_count"] == 3
    assert summary["open_issue_count"] == 47
    assert summary["open_issue_counts_by_type"] == {
        "HARVEST_2025_CODE_NOT_IN_ACTIVE_DATABASE": 29,
        "LE_DEER_2025_DRAW_TO_DATABASE_MISSING_DATABASE_ROW": 6,
        "OIL_2025_DRAW_TO_DATABASE_MISSING_DATABASE_ROW": 12,
    }

    dashboard = {row["check_id"]: row for row in read_rows(DASHBOARD)}
    assert dashboard["le_deer_2025_draw_to_database"]["status"] == "WARN"
    assert dashboard["le_deer_2025_draw_to_database"]["issue_count"] == "6"
    assert dashboard["oil_2025_draw_to_database"]["issue_count"] == "12"
    assert dashboard["harvest_2025_for_2026_database_code_presence"]["issue_count"] == "29"
    assert dashboard["black_bear_2025_to_2026_history_crosswalk"]["status"] == "PASS"


def test_comprehensive_integrity_audit_does_not_hide_structural_failures() -> None:
    run_audit()

    dashboard = read_rows(DASHBOARD)
    fail_rows = [row for row in dashboard if row["status"] == "FAIL"]
    assert fail_rows == []

    open_issues = read_rows(OPEN_ISSUES)
    issue_codes = {row["hunt_code"] for row in open_issues}
    assert {"DB1320", "MB6200", "BI0001", "PD1026"}.issubset(issue_codes)
    assert all(row["severity"] == "WARNING" for row in open_issues)
