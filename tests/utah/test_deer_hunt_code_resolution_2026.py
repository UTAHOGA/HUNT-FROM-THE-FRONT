from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT_SUMMARY = ROOT / "processed_data/2023_deer_odds_audit.json"
PROMOTION_SUMMARY = ROOT / "processed_data/2026_deer_predictive_v2_reference_promotion_summary.json"
RECONCILIATION_SUMMARY = ROOT / "processed_data/2026_deer_hunt_code_reconciliation_summary.json"
HUNT_HEADERS = ROOT / "data_truth/draw_results_truth/extracted/2023_deer_odds_hunt_headers.csv"
RECONCILIATION = ROOT / "data_truth/draw_results_truth/validation/2026_deer_hunt_code_reconciliation.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"

EXPECTED_REFERENCE_PREFIX_COUNTS = {"DB": 15, "LO": 113}
EXPECTED_REFERENCE_SAMPLE_CODES = {"DB0001", "DB1056", "DB1118", "LO0008", "LO1501", "LO1631"}


def test_deer_hunt_code_resolution_runs_and_writes_outputs() -> None:
    subprocess.run([sys.executable, "scripts/resolve-deer-hunt-codes-2026.py"], cwd=ROOT, check=True)

    assert AUDIT_SUMMARY.exists()
    assert PROMOTION_SUMMARY.exists()
    assert RECONCILIATION_SUMMARY.exists()
    assert HUNT_HEADERS.exists()
    assert RECONCILIATION.exists()

    audit = json.loads(AUDIT_SUMMARY.read_text(encoding="utf-8"))
    assert audit["classification"] == "DEER_DRAW_RESULTS_TRUTH_SOURCE_AUDIT"
    assert audit["source_sha256"] == "4188e4c1b712ec1c4973b735b6cb06e489680f15a1b2011857046b49707efabf"
    assert audit["pdf_pages"] == 190
    assert audit["text_lines"] == 7220
    assert audit["hunt_header_rows"] == 189
    assert audit["unique_hunt_header_codes"] == 189
    assert audit["hunt_header_prefix_counts"] == {"DB": 189}
    assert audit["long_csv_db_rows"] == 11718
    assert audit["long_csv_unique_db_codes"] == 189
    assert audit["pdf_header_codes_match_long_csv_codes"] is True
    assert audit["reported_draw_year"] == 2023
    assert audit["model_target_year"] == 2024
    assert audit["blockers"] == 0

    reconciliation = json.loads(RECONCILIATION_SUMMARY.read_text(encoding="utf-8"))
    assert reconciliation["classification"] == "DEER_HUNT_CODE_RECONCILIATION"
    assert reconciliation["target_prefixes"] == ["DB", "LO"]
    assert reconciliation["current_database_code_count"] == 458
    assert reconciliation["draw_results_2023_db_code_count"] == 189
    assert reconciliation["current_database_codes_present_in_2023_deer_odds_count"] == 172
    assert reconciliation["current_database_reconciliation_failure_count"] == 0
    assert reconciliation["blockers"] == 0


def test_deer_reference_codes_promoted_without_modeling_odds() -> None:
    promotion = json.loads(PROMOTION_SUMMARY.read_text(encoding="utf-8"))
    assert promotion["classification"] == "DEER_REFERENCE_PROMOTION"
    assert promotion["target_prefixes"] == ["DB", "LO"]
    assert promotion["promoted_reference_hunt_code_count"] == 128
    assert promotion["promoted_reference_prefix_counts"] == EXPECTED_REFERENCE_PREFIX_COUNTS
    assert promotion["still_missing_predictive_hunt_code_count"] == 0
    assert promotion["duplicate_reference_key_count"] == 0

    promoted_codes = set(promotion["promoted_reference_hunt_codes"])
    assert len(promoted_codes) == 128
    assert EXPECTED_REFERENCE_SAMPLE_CODES.issubset(promoted_codes)

    with PREDICTIVE.open(newline="", encoding="utf-8-sig") as handle:
        reference_rows = [
            row
            for row in csv.DictReader(handle)
            if row["model_version"] == "deer_reference_v1.0.0"
            and row["hunt_code"] in promoted_codes
        ]

    assert len({row["hunt_code"] for row in reference_rows}) == 128
    non_lo_rows = [row for row in reference_rows if not row["hunt_code"].startswith("LO")]
    locked_private_land_lo_rows = [
        row for row in reference_rows if row["hunt_code"] in {"LO0008", "LO0009", "LO0010"}
    ]
    assert {row["algorithm_status"] for row in non_lo_rows} == {"DEER_REFERENCE"}
    assert {row["algorithm_status"] for row in locked_private_land_lo_rows} == {"PRIVATE_LAND_DEER_REFERENCE"}
    assert {row["draw_system_type"] for row in locked_private_land_lo_rows} == {"PRIVATE_LAND_DEER_REFERENCE"}
    assert {row["draw_pool"] for row in locked_private_land_lo_rows} == {"private_land_deer_reference"}
    assert {row["modeled_by_engine"] for row in reference_rows} == {"False"}
    assert {row["probability_model"] for row in reference_rows} == {"NONE"}
    assert {row["display_odds_text"] for row in non_lo_rows} == {"Deer reference only; odds not modeled"}
    assert {row["display_odds_text"] for row in locked_private_land_lo_rows} == {
        "Private-land deer reference only; odds not modeled"
    }
    assert {row["data_quality_grade"] for row in reference_rows} == {"A"}


def test_deer_reconciliation_distinguishes_draw_truth_from_reference_only_codes() -> None:
    with RECONCILIATION.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["hunt_code"]: row for row in csv.DictReader(handle)}

    assert rows["DB1000"]["source_basis"] == "prior_2023_deer_draw_results"
    assert rows["DB1000"]["present_in_2023_deer_odds_pdf"] == "true"
    assert rows["DB1000"]["current_database_reconciliation_status"] == "PASS"

    assert rows["DB0001"]["source_basis"] == "current_2026_tribal_reference_only"
    assert rows["DB0001"]["present_in_2023_deer_odds_pdf"] == "false"
    assert rows["DB0001"]["current_database_reconciliation_status"] == "PASS"

    assert rows["DB1056"]["source_basis"] == "current_2026_special_permit_reference_only"
    assert rows["DB1118"]["source_basis"] == "current_2026_special_permit_reference_only"
    assert rows["LO1501"]["source_basis"] == "current_2026_private_land_reference_only"
