from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "processed_data/2026_turkey_guidebook_audit.json"
TEXT_LINES = ROOT / "data_truth/regulations_truth/normalized/2026_turkey_guidebook_text_lines.csv"
NUMBER_TOKENS = ROOT / "data_truth/regulations_truth/normalized/2026_turkey_guidebook_number_tokens.csv"
EXPECTED_CHECKS = ROOT / "data_truth/regulations_truth/normalized/2026_turkey_guidebook_expected_text_checks.csv"
RECONCILIATION = ROOT / "data_truth/regulations_truth/normalized/2026_turkey_guidebook_hunt_code_name_reconciliation.csv"


def test_turkey_guidebook_audit_runs_and_writes_truth_outputs() -> None:
    subprocess.run([sys.executable, "scripts/audit-turkey-guidebook-2026.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert TEXT_LINES.exists()
    assert NUMBER_TOKENS.exists()
    assert EXPECTED_CHECKS.exists()
    assert RECONCILIATION.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "REGULATION_AND_GUIDEBOOK_TRUTH_SOURCE_AUDIT"
    assert summary["source_sha256"] == "c2d54eff8304c6b93d549cc59cba17a5df2cb0fcc22cb723d3befc088beab149"
    assert summary["pdf_pages"] == 45
    assert summary["text_lines"] == 2521
    assert summary["number_tokens"] == 1968
    assert summary["expected_text_checks"] == 53
    assert summary["expected_text_anchor_failures"] == 0
    assert summary["guidebook_printed_hunt_code_count"] == 7
    assert summary["database_name_resolved_hunt_code_count"] == 7
    assert summary["hunt_code_reconciliation_failures"] == 0
    assert summary["guidebook_bonus_point_codes"] == ["TKY"]
    assert summary["blockers"] == 0


def test_turkey_guidebook_hunt_codes_resolve_to_database_names() -> None:
    with RECONCILIATION.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["guidebook_code"]: row for row in csv.DictReader(handle)}

    assert rows["TK1003"]["guidebook_name"] == "Central"
    assert rows["TK1003"]["database_hunt_name"] == "Central Area"
    assert rows["TK1003"]["name_resolution_status"] == "true"

    assert rows["TK1007"]["database_hunt_name"] == "Southern Area"
    assert rows["TK1018"]["database_hunt_name"] == "Pahvant Ensign CWMU"
    assert rows["TK1021"]["database_hunt_name"] == "East Zion CWMU"

    assert rows["TKY"]["code_type"] == "bonus_point_code"
    assert rows["TKY"]["database_present"] == "false"
    assert rows["TKY"]["status"] == "PASS_BONUS_POINT_CODE_NOT_DATABASE_HUNT"


def test_turkey_expected_text_checks_all_pass() -> None:
    with EXPECTED_CHECKS.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    assert {row["status"] for row in rows} == {"PASS"}
    assert any(row["check_id"] == "limited_entry_codes" for row in rows)
    assert any(row["check_id"] == "cwmu_codes" for row in rows)
