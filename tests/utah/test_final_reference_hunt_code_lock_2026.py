from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCK_CSV = ROOT / "data_truth/permit_overlay_truth/normalized/final_reference_hunt_code_lock_2026.csv"
SUMMARY = ROOT / "processed_data/final_reference_hunt_code_lock_2026_summary.json"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"
CONSERVATION_CYCLE = ROOT / "data_truth/permit_overlay_truth/normalized/conservation_permit_cycle_rows_2022_2027.csv"

LOCK_CODES = {"RS0001", "RS1000", "RS1001", "RS1003", "RS1006", "BI6527", "BI6538", "EX1000", "CG9999"}
REFERENCE_CODES = LOCK_CODES - {"RS0001"}
FULL_SPLIT_CODES = {"RS0001", "RS1001", "RS1003", "RS1006"}
NO_QUOTA_CODES = LOCK_CODES - FULL_SPLIT_CODES


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_final_reference_lock_runs_and_writes_output_spreadsheet() -> None:
    subprocess.run([sys.executable, "scripts/lock-final-reference-hunt-codes-2026.py"], cwd=ROOT, check=True)

    rows = read_rows(LOCK_CSV)
    assert {row["Hunt Code"] for row in rows} == LOCK_CODES
    assert {"Non Res", "Res", "Total"}.issubset(rows[0])

    by_code = {row["Hunt Code"]: row for row in rows}
    for code in FULL_SPLIT_CODES:
        assert by_code[code]["Res"] == "1"
        assert by_code[code]["Non Res"] == "0"
        assert by_code[code]["Total"] == "1"
        assert by_code[code]["Permit Status"] == "FULL_SPLIT"

    for code in NO_QUOTA_CODES:
        assert not by_code[code]["Res"]
        assert not by_code[code]["Non Res"]
        assert not by_code[code]["Total"]
        assert by_code[code]["Permit Status"] == "NO_QUOTA_PUBLISHED"

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "FINAL_REFERENCE_HUNT_CODE_LOCK_2026"
    assert summary["blocker_count"] == 0
    assert summary["lock_code_count"] == 9
    assert set(summary["predictive_reference_codes_locked"]) == REFERENCE_CODES
    assert summary["permit_status_counts"] == {"FULL_SPLIT": 4, "NO_QUOTA_PUBLISHED": 5}


def test_rocky_bighorn_counts_come_from_conservation_permit_database() -> None:
    cycle_rows = read_rows(CONSERVATION_CYCLE)
    source_areas = {
        row["area"]: row
        for row in cycle_rows
        if row["cycle"] == "2025-2027"
        and row["species_family"] == "Rocky Mountain Bighorn Sheep"
        and row["condition_or_weapon"] == "Any Legal Weapon"
    }
    expected_areas = {
        "Statewide",
        "Book Cliffs, South",
        "Box Elder, Newfoundland Mtns (late)",
        "Nine Mile, Gray Canyon",
    }
    assert expected_areas.issubset(source_areas)
    assert {source_areas[area]["permit_count"] for area in expected_areas} == {"1"}


def test_final_reference_predictive_rows_are_non_modeled_except_existing_sportsman() -> None:
    rows = [row for row in read_rows(PREDICTIVE) if row["hunt_code"] in LOCK_CODES]
    by_code = {row["hunt_code"]: row for row in rows}
    assert set(by_code) == LOCK_CODES

    assert by_code["RS0001"]["draw_system_type"] == "SPORTSMAN_PERMIT"
    assert by_code["RS0001"]["sportsman_permit_count"] == "1"

    for code in REFERENCE_CODES:
        row = by_code[code]
        assert row["modeled_by_engine"] == "False"
        assert row["probability_model"] == "NONE"
        assert row["permit_allotment_2026_status"] in {"FULL_SPLIT", "NO_QUOTA_PUBLISHED"}
        assert row["display_odds_text"].endswith("odds not modeled")

    for code in {"RS1001", "RS1003", "RS1006"}:
        assert by_code[code]["permit_allotment_2026_res"] == "1"
        assert by_code[code]["permit_allotment_2026_nr"] == "0"
        assert by_code[code]["permit_allotment_2026_total"] == "1"

    for code in NO_QUOTA_CODES:
        if code == "RS0001":
            continue
        assert not by_code[code]["permit_allotment_2026_res"]
        assert not by_code[code]["permit_allotment_2026_nr"]
        assert not by_code[code]["permit_allotment_2026_total"]


def test_final_reference_lock_validates_all_runtime_surfaces() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    for validation in summary["surface_validations"]:
        assert validation["missing_codes"] == []
        assert validation["quota_mismatch_count"] == 0
        assert validation["bad_predictive_row_count"] == 0
