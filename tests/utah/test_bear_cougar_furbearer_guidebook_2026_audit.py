from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "processed_data/2026_bear_cougar_furbearer_guidebook_audit.json"
TEXT_LINES = ROOT / "data_truth/regulations_truth/normalized/2026_bear_cougar_furbearer_guidebook_text_lines.csv"
NUMBER_TOKENS = ROOT / "data_truth/regulations_truth/normalized/2026_bear_cougar_furbearer_guidebook_number_tokens.csv"
EXPECTED_CHECKS = (
    ROOT / "data_truth/regulations_truth/normalized/2026_bear_cougar_furbearer_guidebook_expected_text_checks.csv"
)
BEAR_HUNTS = ROOT / "data_truth/regulations_truth/normalized/2026_bear_cougar_furbearer_guidebook_bear_hunt_tables.csv"


def test_bear_cougar_furbearer_guidebook_audit_runs_and_reconciles_codes() -> None:
    subprocess.run([sys.executable, "scripts/audit-bear-cougar-furbearer-guidebook-2026.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert TEXT_LINES.exists()
    assert NUMBER_TOKENS.exists()
    assert EXPECTED_CHECKS.exists()
    assert BEAR_HUNTS.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "REGULATION_AND_GUIDEBOOK_TRUTH_SOURCE_AUDIT"
    assert summary["source_sha256"] == "57a7a7c4b40196faf34251b260d30946aaaf23cbe0755e916508fc7d70b5b5f6"
    assert summary["pdf_pages"] == 88
    assert summary["text_lines"] == 3501
    assert summary["number_tokens"] == 2506
    assert summary["expected_text_checks"] == 55
    assert summary["expected_text_anchor_failures"] == 0
    assert summary["bear_guidebook_hunt_code_count"] == 99
    assert summary["bear_codes_missing_database"] == []
    assert summary["bear_codes_missing_predictive"] == []
    assert summary["blockers"] == 0


def test_dolores_triangle_and_restricted_pursuit_rows_are_traceable() -> None:
    with BEAR_HUNTS.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["hunt_code"]: row for row in csv.DictReader(handle)}

    assert rows["BR7021"]["database_hunt_name"] == "Dolores Triangle"
    assert rows["BR7021"]["permits_2026_total"] == "2"
    assert rows["BR7126"]["database_hunt_name"] == "Dolores Triangle"
    assert rows["BR7126"]["permits_2026_total"] == "6"
    assert rows["BR7238"]["database_hunt_name"] == "Dolores Triangle"
    assert rows["BR7238"]["permits_2026_total"] == "2"
    assert rows["BR1015"]["database_present"] == "true"
    assert rows["BR1015"]["predictive_present"] == "true"


def test_expected_text_checks_all_pass() -> None:
    with EXPECTED_CHECKS.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    assert {row["status"] for row in rows} == {"PASS"}
    assert any(row["check_id"] == "bear_pursuit_fee" for row in rows)
    assert any(row["check_id"] == "cougar_no_extra_permit" for row in rows)
