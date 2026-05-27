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
HARVEST_RESOLUTIONS = ROOT / "data_truth" / "crosswalk_truth" / "normalized" / "harvest_only_2025_code_resolutions.csv"


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
    assert summary["database"]["row_count"] == 1449
    assert summary["database"]["unique_hunt_code_count"] == 1449
    assert summary["database"]["duplicate_hunt_code_count"] == 0
    assert summary["database"]["blank_boundary_id_count"] == 0
    assert summary["retired_current_codes"]["ledger_row_count"] == 17
    assert summary["retired_current_codes"]["retired_codes_still_active_count"] == 0
    assert summary["harvest_only_resolutions"]["ledger_row_count"] == 4
    assert summary["harvest_only_resolutions"]["resolved_codes"] == ["BI0001", "DB1774", "PB5343", "PD1041"]
    assert summary["permit_overlay_numeric_issue_total"] == 0


def test_comprehensive_integrity_audit_tracks_known_review_queue() -> None:
    run_audit()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["review_warning_count"] == 0
    assert summary["open_issue_count"] == 0
    assert summary["open_issue_counts_by_type"] == {}

    dashboard = {row["check_id"]: row for row in read_rows(DASHBOARD)}
    assert dashboard["le_deer_2025_draw_to_database"]["status"] == "PASS"
    assert dashboard["le_deer_2025_draw_to_database"]["issue_count"] == "0"
    assert dashboard["oil_2025_draw_to_database"]["issue_count"] == "0"
    assert dashboard["harvest_only_2025_code_resolution_ledger"]["status"] == "PASS"
    assert dashboard["harvest_2025_for_2026_database_code_presence"]["issue_count"] == "0"
    assert dashboard["black_bear_2025_to_2026_history_crosswalk"]["status"] == "PASS"


def test_comprehensive_integrity_audit_does_not_hide_structural_failures() -> None:
    run_audit()

    dashboard = read_rows(DASHBOARD)
    fail_rows = [row for row in dashboard if row["status"] == "FAIL"]
    assert fail_rows == []

    open_issues = read_rows(OPEN_ISSUES)
    assert open_issues == []


def test_harvest_only_codes_obey_definite_2026_remap_rule() -> None:
    run_audit()

    rows = {row["source_hunt_code"]: row for row in read_rows(HARVEST_RESOLUTIONS)}
    assert rows["PB5343"]["resolution_status"] == "DISCONTINUED_2026_NO_DEFINITE_ONE_TO_ONE_MATCH"
    assert rows["PB5343"]["maps_to_draw_odds_code"] == "NO_CURRENT_2026_DRAW_CODE"
    assert rows["DB1774"]["resolution_status"] == "DISCONTINUED_2026_NO_DEFINITE_ONE_TO_ONE_MATCH"
    assert rows["DB1774"]["maps_to_draw_odds_code"] == "NO_CURRENT_2026_DRAW_CODE"
    assert rows["PD1041"]["mapped_hunt_code"] == "PD1052"
    assert rows["PD1041"]["mapped_hunt_name"] == "Heist CWMU"
    assert rows["PD1041"]["mapped_species"] == "Pronghorn"
    assert rows["PD1041"]["mapped_sex_type"] == "Doe"
    assert rows["PD1041"]["mapped_weapon"] == "Any Legal Weapon"
