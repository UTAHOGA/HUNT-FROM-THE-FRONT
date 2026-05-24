from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PRIOR_SUMMARY = ROOT / "processed_data/2025_turkey_guidebook_audit.json"
FULL_SUMMARY = ROOT / "processed_data/2026_turkey_full_hunt_code_reconciliation_summary.json"
PROMOTION_SUMMARY = ROOT / "processed_data/2026_turkey_predictive_v2_reference_promotion_summary.json"
PRIOR_EXPECTED_CHECKS = ROOT / "data_truth/regulations_truth/normalized/2025_turkey_guidebook_expected_text_checks.csv"
PRIOR_RECONCILIATION = ROOT / "data_truth/regulations_truth/normalized/2025_turkey_guidebook_hunt_code_name_reconciliation.csv"
FULL_RECONCILIATION = ROOT / "data_truth/regulations_truth/normalized/2026_turkey_full_hunt_code_reconciliation.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"

EXPECTED_REFERENCE_CODES = {
    "TK1000",
    "TK1001",
    "TK1012",
    "TK1013",
    "TK1014",
    "TK1015",
    "TK1016",
    "TK1019",
    "TK1020",
    "TK1022",
}

EXPECTED_NOT_PRINTED_CURRENT_DATABASE_CODES = EXPECTED_REFERENCE_CODES | {"TK0001"}


def test_turkey_hunt_code_resolution_runs_and_writes_outputs() -> None:
    subprocess.run([sys.executable, "scripts/resolve-turkey-hunt-codes-2026.py"], cwd=ROOT, check=True)

    assert PRIOR_SUMMARY.exists()
    assert FULL_SUMMARY.exists()
    assert PROMOTION_SUMMARY.exists()
    assert PRIOR_EXPECTED_CHECKS.exists()
    assert PRIOR_RECONCILIATION.exists()
    assert FULL_RECONCILIATION.exists()

    prior = json.loads(PRIOR_SUMMARY.read_text(encoding="utf-8"))
    assert prior["classification"] == "PRIOR_YEAR_TURKEY_GUIDEBOOK_TRUTH_SOURCE_AUDIT"
    assert prior["source_sha256"] == "5d6af291900a3c790c1673ad0e520d38d2ddc0ddbb2392f67426b1a45bc2e8a3"
    assert prior["pdf_pages"] == 63
    assert prior["expected_text_anchor_failures"] == 0
    assert prior["guidebook_printed_hunt_code_count"] == 7
    assert prior["guidebook_bonus_point_codes"] == ["TKY"]
    assert prior["database_name_resolved_hunt_code_count"] == 7
    assert prior["hunt_code_reconciliation_failures"] == 0
    assert prior["blockers"] == 0

    full = json.loads(FULL_SUMMARY.read_text(encoding="utf-8"))
    assert full["classification"] == "TURKEY_FULL_HUNT_CODE_RECONCILIATION"
    assert full["current_database_turkey_code_count"] == 18
    assert full["guidebook_2026_printed_current_hunt_code_count"] == 7
    assert full["guidebook_2025_printed_hunt_code_count"] == 7
    assert full["bonus_point_codes"] == ["TKY"]
    assert full["current_database_codes_not_printed_in_2026_guidebook_code_list_count"] == 11
    assert set(full["current_database_codes_not_printed_in_2026_guidebook_code_list"]) == EXPECTED_NOT_PRINTED_CURRENT_DATABASE_CODES
    assert full["current_predictive_v2_turkey_code_count"] == 18
    assert full["current_database_reconciliation_failure_count"] == 0
    assert full["blockers"] == 0


def test_turkey_reference_codes_promoted_without_modeling_odds() -> None:
    promotion = json.loads(PROMOTION_SUMMARY.read_text(encoding="utf-8"))
    assert promotion["classification"] == "TURKEY_GUIDEBOOK_REFERENCE_PROMOTION"
    assert promotion["current_database_turkey_code_count"] == 18
    assert promotion["promoted_reference_hunt_code_count"] == 10
    assert promotion["still_missing_predictive_hunt_code_count"] == 0
    assert promotion["duplicate_reference_key_count"] == 0
    assert set(promotion["promoted_reference_hunt_codes"]) == EXPECTED_REFERENCE_CODES

    with PREDICTIVE.open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for row in csv.DictReader(handle) if row["hunt_code"] in EXPECTED_REFERENCE_CODES]

    reference_rows = [row for row in rows if row["model_version"] == "turkey_guidebook_reference_v1.0.0"]
    assert {row["hunt_code"] for row in reference_rows} == EXPECTED_REFERENCE_CODES
    assert {row["algorithm_status"] for row in reference_rows} == {"TURKEY_GUIDEBOOK_REFERENCE"}
    assert {row["modeled_by_engine"] for row in reference_rows} == {"False"}
    assert {row["probability_model"] for row in reference_rows} == {"NONE"}
    assert {row["display_odds_text"] for row in reference_rows} == {"Turkey reference only; odds not modeled"}


def test_full_reconciliation_classifies_database_only_turkey_codes() -> None:
    with FULL_RECONCILIATION.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["hunt_code"]: row for row in csv.DictReader(handle)}

    assert rows["TK1003"]["code_resolution_class"] == "GUIDEBOOK_PRINTED_CURRENT_HUNT_CODE"
    assert rows["TK1003"]["printed_in_2026_guidebook"] == "true"
    assert rows["TK1003"]["current_database_reconciliation_status"] == "PASS"

    assert rows["TK1000"]["code_resolution_class"] == "CURRENT_DATABASE_PREDICTIVE_REFERENCE_NOT_PRINTED_IN_GUIDEBOOK_CODE_LIST"
    assert "Spring general-season hunt is described as statewide" in rows["TK1000"]["guidebook_basis"]

    assert rows["TK1001"]["hunt_type"] == "Fall Management"
    assert "Fall management harvest Northern Region" in rows["TK1001"]["guidebook_basis"]

    assert rows["TK1012"]["hunt_type"] == "Conservation"
    assert "Conservation permits are described" in rows["TK1012"]["guidebook_basis"]

    assert rows["TK1022"]["hunt_type"] == "Fall Management"
    assert "2025-26 guidebook" in rows["TK1022"]["guidebook_basis"]


def test_prior_guidebook_bonus_point_code_is_not_treated_as_missing_hunt() -> None:
    with PRIOR_RECONCILIATION.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["guidebook_code"]: row for row in csv.DictReader(handle)}

    assert rows["TKY"]["code_type"] == "bonus_point_code"
    assert rows["TKY"]["database_present"] == "false"
    assert rows["TKY"]["status"] == "PASS_BONUS_POINT_CODE_NOT_DATABASE_HUNT"

    with PRIOR_EXPECTED_CHECKS.open(newline="", encoding="utf-8-sig") as handle:
        checks = list(csv.DictReader(handle))
    assert {row["status"] for row in checks} == {"PASS"}
