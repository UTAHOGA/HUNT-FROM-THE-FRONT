from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

LOCK_CSV = ROOT / "data_truth/permit_overlay_truth/normalized/desert_bighorn_conservation_permit_code_lock_2026.csv"
SUMMARY = ROOT / "processed_data/desert_bighorn_conservation_permit_code_lock_2026_summary.json"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
HUNT_MASTER = ROOT / "processed_data/hunt_master_enriched.csv"
DRAW_REALITY = ROOT / "processed_data/draw_reality_engine.csv"
POINT_LADDER = ROOT / "processed_data/point_ladder_view.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"
CONSERVATION_CYCLE = ROOT / "data_truth/permit_overlay_truth/normalized/conservation_permit_cycle_rows_2022_2027.csv"

LOCK_CODES = {"DS1000", "DS1002", "DS1003", "DS1004", "DS1006", "DS1007", "DS6605"}
REFERENCE_CODES = LOCK_CODES - {"DS1000"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def grouped_rows(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped = {code: [] for code in LOCK_CODES}
    for row in read_rows(path):
        code = row.get("hunt_code", "")
        if code in grouped:
            grouped[code].append(row)
    return grouped


def test_desert_bighorn_conservation_lock_script_runs_and_writes_outputs() -> None:
    subprocess.run([sys.executable, "scripts/lock-desert-bighorn-conservation-permit-codes-2026.py"], cwd=ROOT, check=True)

    assert LOCK_CSV.exists()
    assert SUMMARY.exists()

    rows = read_rows(LOCK_CSV)
    assert {row["hunt_code"] for row in rows} == LOCK_CODES
    assert {"Non Res", "Res", "Total"}.issubset(rows[0])
    assert {row["Total"] for row in rows} == {"1"}
    assert {row["Res"] for row in rows} == {"1"}
    assert {row["Non Res"] for row in rows} == {"0"}

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "DESERT_BIGHORN_CONSERVATION_PERMIT_CODE_LOCK_2026"
    assert summary["blockers"] == 0
    assert summary["lock_code_count"] == 7
    assert set(summary["predictive_reference_codes_locked"]) == REFERENCE_CODES
    assert summary["predictive_reference_code_count_locked"] == 6


def test_desert_bighorn_counts_come_from_conservation_permit_cycle_database() -> None:
    cycle_rows = read_rows(CONSERVATION_CYCLE)
    source_areas = {
        row["area"]: row
        for row in cycle_rows
        if row["cycle"] == "2025-2027"
        and row["species_family"] == "Desert Bighorn Sheep"
        and row["condition_or_weapon"] == "Any Legal Weapon"
    }

    expected_areas = {
        "Statewide",
        "Kaiparowits, East",
        "Kaiparowits, Escalante",
        "Kaiparowits, West",
        "Pine Valley, Beaver Dam",
        "San Rafael, Dirty Devil",
        "San Rafael, South",
    }
    assert expected_areas.issubset(source_areas)
    assert {source_areas[area]["permit_count"] for area in expected_areas} == {"1"}


def test_locked_desert_bighorn_codes_have_one_resident_total_on_all_surfaces() -> None:
    for path in [DATABASE, HUNT_MASTER, DRAW_REALITY, POINT_LADDER, PREDICTIVE]:
        grouped = grouped_rows(path)
        assert all(grouped[code] for code in LOCK_CODES), path
        for code in LOCK_CODES:
            for row in grouped[code]:
                assert row.get("permits_2026_res", "1") == "1"
                assert row.get("permits_2026_nr", "0") == "0"
                assert row.get("permits_2026_total", "1") == "1"
                assert row.get("public_permits_2026", "1") == "1"
                assert row.get("quota_2026_total", "1") == "1"
                assert row.get("permit_allotment_2026_total", "1") == "1"
                assert row.get("permit_status", "FULL_SPLIT") == "FULL_SPLIT"


def test_missing_ds_codes_are_promoted_as_non_modeled_reference_rows() -> None:
    predictive = grouped_rows(PREDICTIVE)
    for code in REFERENCE_CODES:
        assert len(predictive[code]) == 1
        row = predictive[code][0]
        assert row["model_version"] == "desert_bighorn_conservation_reference_v1.0.0"
        assert row["modeled_by_engine"] == "False"
        assert row["probability_model"] == "NONE"
        assert row["display_odds_text"] == "Conservation reference only; odds not modeled"

    sportsman = predictive["DS1000"]
    assert len(sportsman) == 1
    assert sportsman[0]["algorithm_status"] == "MODELED_SPORTSMAN_DRAW"
    assert sportsman[0]["sportsman_permit_count"] == "1"
