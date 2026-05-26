from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCK_CSV = ROOT / "data_truth/permit_overlay_truth/normalized/private_land_deer_hunt_code_lock_2026.csv"
SUMMARY = ROOT / "processed_data/private_land_deer_hunt_code_lock_2026_summary.json"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"

PRIVATE_LAND_DEER_CODES = {
    "LD1001",
    "LD1004",
    "LD1006",
    "LD1019",
    "LD1023",
    "LD1108",
    "LO0008",
    "LO0009",
    "LO0010",
}

LD_CODES = {code for code in PRIVATE_LAND_DEER_CODES if code.startswith("LD")}
LO_CODES = {code for code in PRIVATE_LAND_DEER_CODES if code.startswith("LO")}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_private_land_deer_lock_runs_and_writes_no_quota_spreadsheet() -> None:
    subprocess.run([sys.executable, "scripts/lock-private-land-deer-hunt-codes-2026.py"], cwd=ROOT, check=True)

    assert LOCK_CSV.exists()
    assert SUMMARY.exists()

    rows = read_rows(LOCK_CSV)
    assert {row["Hunt Code"] for row in rows} == PRIVATE_LAND_DEER_CODES
    assert {"Non Res", "Res", "Total"}.issubset(rows[0])
    assert {row["Permit Status"] for row in rows} == {"NO_QUOTA_PUBLISHED"}
    assert all(not row["Non Res"] and not row["Res"] and not row["Total"] for row in rows)

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "PRIVATE_LAND_DEER_HUNT_CODE_LOCK_2026"
    assert summary["blocker_count"] == 0
    assert summary["locked_hunt_code_count"] == 9
    assert set(summary["ld_predictive_reference_codes_added_this_run"]) <= LD_CODES
    assert set(summary["existing_lo_reference_codes_checked"]) == LO_CODES
    assert summary["permit_status_counts"] == {"NO_QUOTA_PUBLISHED": 9}


def test_private_land_deer_predictive_rows_are_non_modeled_reference_rows() -> None:
    predictive = read_rows(PREDICTIVE)
    rows = [row for row in predictive if row["hunt_code"] in PRIVATE_LAND_DEER_CODES]
    by_code = {row["hunt_code"]: row for row in rows}

    assert set(by_code) == PRIVATE_LAND_DEER_CODES
    assert {by_code[code]["model_version"] for code in LD_CODES} == {"private_land_deer_reference_v1.0.0"}
    assert {by_code[code]["model_version"] for code in LO_CODES} == {"deer_reference_v1.0.0"}
    assert {row["species"] for row in rows} == {"Deer"}
    assert {row["sex_type"] for row in rows} == {"Buck"}
    assert {row["draw_system_type"] for row in rows} == {"PRIVATE_LAND_DEER_REFERENCE"}
    assert {row["draw_pool"] for row in rows} == {"private_land_deer_reference"}
    assert {row["residency"] for row in rows} == {"Private Land Only"}
    assert {row["modeled_by_engine"] for row in rows} == {"False"}
    assert {row["probability_model"] for row in rows} == {"NONE"}
    assert {row["display_odds_text"] for row in rows} == {"Private-land deer reference only; odds not modeled"}
    assert {row["permit_allotment_2026_status"] for row in rows} == {"NO_QUOTA_PUBLISHED"}
    assert all(row["private_land_only_flag"] == "True" for row in rows)
    assert all(not row["permit_allotment_2026_res"] for row in rows)
    assert all(not row["permit_allotment_2026_nr"] for row in rows)
    assert all(not row["permit_allotment_2026_total"] for row in rows)
    assert all(not row["quota_2026_total"] for row in rows)


def test_private_land_deer_lock_validates_all_runtime_surfaces() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    for validation in summary["surface_validations"]:
        assert validation["missing_codes"] == []
        assert validation["quota_leak_count"] == 0
        assert validation["bad_status_count"] == 0
        assert validation["bad_predictive_row_count"] == 0
