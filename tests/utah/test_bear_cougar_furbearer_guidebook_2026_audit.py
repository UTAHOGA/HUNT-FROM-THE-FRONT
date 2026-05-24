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
BEAR_CODE_RECONCILIATION = (
    ROOT
    / "data_truth/regulations_truth/normalized/2026_bear_cougar_furbearer_guidebook_bear_hunt_code_reconciliation.csv"
)


def test_bear_cougar_furbearer_guidebook_audit_runs_and_reconciles_codes() -> None:
    subprocess.run([sys.executable, "scripts/audit-bear-cougar-furbearer-guidebook-2026.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert TEXT_LINES.exists()
    assert NUMBER_TOKENS.exists()
    assert EXPECTED_CHECKS.exists()
    assert BEAR_HUNTS.exists()
    assert BEAR_CODE_RECONCILIATION.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "REGULATION_AND_GUIDEBOOK_TRUTH_SOURCE_AUDIT"
    assert summary["source_sha256"] == "57a7a7c4b40196faf34251b260d30946aaaf23cbe0755e916508fc7d70b5b5f6"
    assert summary["pdf_pages"] == 88
    assert summary["text_lines"] == 3501
    assert summary["number_tokens"] == 2506
    assert summary["expected_text_checks"] == 55
    assert summary["expected_text_anchor_failures"] == 0
    assert summary["bear_guidebook_hunt_code_count"] == 99
    assert summary["bear_current_database_code_count"] == 106
    assert summary["bear_current_predictive_code_count"] == 106
    assert summary["bear_current_hunt_master_code_count"] == 106
    assert summary["bear_current_point_ladder_code_count"] == 106
    assert summary["bear_database_reference_codes_not_printed_in_hunt_table_count"] == 7
    assert summary["bear_database_reference_codes_not_printed_in_hunt_table"] == [
        "BR1000",
        "BR1001",
        "BR1007",
        "BR1018",
        "BR7237",
        "BR7307",
        "BR7324",
    ]
    assert summary["bear_historical_only_draw_reality_code_count"] == 14
    assert summary["bear_codes_missing_database"] == []
    assert summary["bear_codes_missing_predictive"] == []
    assert summary["bear_current_code_reconciliation_failures"] == 0
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


def test_full_bear_code_universe_is_resolved() -> None:
    with BEAR_CODE_RECONCILIATION.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 120
    status_counts = {}
    for row in rows:
        status_counts[row["resolution_status"]] = status_counts.get(row["resolution_status"], 0) + 1

    assert status_counts == {
        "PASS_CURRENT_DATABASE_REFERENCE_CODE_RESOLVED": 7,
        "PASS_CURRENT_GUIDEBOOK_CODE_RESOLVED": 99,
        "INFO_HISTORICAL_ONLY_NOT_CURRENT_2026_DATABASE": 14,
    }

    rows_by_code = {row["hunt_code"]: row for row in rows}
    assert rows_by_code["BR1001"]["database_hunt_name"] == "Black Bear Harvest Objective Units"
    assert rows_by_code["BR1007"]["database_hunt_name"] == "Black Bear Pursuit - Resident"
    assert rows_by_code["BR1018"]["database_hunt_name"] == "Black Bear Pursuit - Nonresident"
    assert rows_by_code["BR7237"]["database_hunt_name"] == "Monroe"
    assert rows_by_code["BR7307"]["predictive_algorithm_status"] == "EXCLUDED_NOT_PREDICTIVE_DRAW"
    assert rows_by_code["BR7324"]["predictive_algorithm_status"] == "EXCLUDED_NOT_PREDICTIVE_DRAW"
    assert rows_by_code["BR7008"]["source_class"] == "HISTORICAL_DRAW_REALITY_ONLY_CODE"
