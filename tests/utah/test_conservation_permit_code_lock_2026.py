from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

LOCK_CSV = ROOT / "data_truth/permit_overlay_truth/normalized/conservation_permit_hunt_code_lock_2026.csv"
SUMMARY = ROOT / "processed_data/conservation_permit_hunt_code_lock_2026_summary.json"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
HUNT_MASTER = ROOT / "processed_data/hunt_master_enriched.csv"
DRAW_REALITY = ROOT / "processed_data/draw_reality_engine.csv"
POINT_LADDER = ROOT / "processed_data/point_ladder_view.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"

NO_QUOTA_CODES = {"EA1180", "EA1270", "EA1271", "EA2041", "EA2045"}
TOTAL_ONLY_CODES = {"EB3128", "EB3209"}
LOCK_CODES = NO_QUOTA_CODES | TOTAL_ONLY_CODES


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def grouped_rows(path: Path) -> dict[str, list[dict[str, str]]]:
    rows = {code: [] for code in LOCK_CODES}
    for row in read_rows(path):
        code = row.get("hunt_code", "")
        if code in rows:
            rows[code].append(row)
    return rows


def test_conservation_permit_lock_script_runs_and_writes_trace_outputs() -> None:
    subprocess.run([sys.executable, "scripts/lock-conservation-permit-hunt-codes-2026.py"], cwd=ROOT, check=True)

    assert LOCK_CSV.exists()
    assert SUMMARY.exists()

    lock_rows = read_rows(LOCK_CSV)
    assert {row["hunt_code"] for row in lock_rows} == LOCK_CODES
    assert {"Non Res", "Res", "Total"}.issubset(lock_rows[0])

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "CONSERVATION_PERMIT_HUNT_CODE_LOCK_2026"
    assert summary["blockers"] == 0
    assert summary["lock_code_count"] == 7
    assert set(summary["no_quota_published_codes"]) == NO_QUOTA_CODES
    assert set(summary["total_only_codes"]) == TOTAL_ONLY_CODES
    assert summary["stale_quota_fixed_codes"] == ["EA1180"]


def test_locked_conservation_codes_are_present_on_all_reference_surfaces() -> None:
    for path in [DATABASE, HUNT_MASTER, DRAW_REALITY, POINT_LADDER, PREDICTIVE]:
        grouped = grouped_rows(path)
        assert set(grouped) == LOCK_CODES
        assert all(grouped[code] for code in LOCK_CODES), path


def test_antlerless_conservation_codes_do_not_carry_public_quota_values() -> None:
    for path in [DATABASE, HUNT_MASTER, DRAW_REALITY, POINT_LADDER, PREDICTIVE]:
        grouped = grouped_rows(path)
        for code in NO_QUOTA_CODES:
            for row in grouped[code]:
                assert row.get("permits_2026_total", "") == ""
                assert row.get("permit_allotment_2026_total", "") == ""
                assert row.get("public_permits_2026", "") == ""
                assert row.get("quota_2026_total", "") == ""
                assert row.get("permit_status", "NO_QUOTA_PUBLISHED") == "NO_QUOTA_PUBLISHED"
                assert row.get("permit_allotment_2026_status", "NO_QUOTA_PUBLISHED") == "NO_QUOTA_PUBLISHED"


def test_elk_bull_conservation_codes_are_total_only_reference_records() -> None:
    for path in [DATABASE, HUNT_MASTER, DRAW_REALITY, POINT_LADDER, PREDICTIVE]:
        grouped = grouped_rows(path)
        for code in TOTAL_ONLY_CODES:
            for row in grouped[code]:
                assert row.get("permits_2026_total", "1") == "1"
                assert row.get("permit_allotment_2026_total", "1") == "1"
                assert row.get("public_permits_2026", "1") == "1"
                assert row.get("quota_2026_total", "1") == "1"
                assert row.get("permit_status", "TOTAL_ONLY") == "TOTAL_ONLY"
                assert row.get("permit_allotment_2026_status", "TOTAL_ONLY") == "TOTAL_ONLY"


def test_predictive_rows_remain_reference_only_and_non_modeled() -> None:
    predictive = grouped_rows(PREDICTIVE)
    for code in NO_QUOTA_CODES:
        assert len(predictive[code]) == 1
        row = predictive[code][0]
        assert row["model_version"] == "antlerless_reference_v1.0.0"
        assert row["modeled_by_engine"] == "False"
        assert row["probability_model"] == "NONE"
        assert row["display_odds_text"] == "Antlerless conservation reference only; odds not modeled"

    for code in TOTAL_ONLY_CODES:
        assert len(predictive[code]) == 1
        row = predictive[code][0]
        assert row["model_version"] == "elk_bull_reference_v1.0.0"
        assert row["modeled_by_engine"] == "False"
        assert row["probability_model"] == "NONE"
        assert row["display_odds_text"] == "Elk bull reference only; odds not modeled"
