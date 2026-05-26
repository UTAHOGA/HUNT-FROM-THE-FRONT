from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
LIVE_SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/live_dwr_permit_numbers_vs_DATABASE_2026_summary.json"
COMPREHENSIVE_LIVE_SUMMARY = (
    ROOT / "data_truth/crosswalk_truth/validation/live_dwr_permit_numbers_comprehensive_vs_DATABASE_2026_summary.json"
)
EXPO_SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/expo_hard_copy_promoted_to_DATABASE_2026_summary.json"
EXPO_TOTAL_ONLY_CSV = ROOT / "data_truth/draw_results_truth/normalized/expo_permit_draw_results_2026_total_only.csv"
EXPO_TOTAL_ONLY_SUMMARY = (
    ROOT / "data_truth/draw_results_truth/validation/expo_permit_draw_results_2026_total_only_summary.json"
)
SHEEP_SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/sheep_sex_type_normalization_2026_summary.json"
REVIEWED_CORRECTIONS_SUMMARY = (
    ROOT / "data_truth/crosswalk_truth/validation/reviewed_live_permit_corrections_2026_summary.json"
)


def _database_by_code() -> dict[str, dict[str, str]]:
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        return {row["hunt_code"]: row for row in csv.DictReader(handle)}


def _expo_total_only_rows() -> list[dict[str, str]]:
    with EXPO_TOTAL_ONLY_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_live_dwr_comparison_has_no_numeric_mismatches_after_shape_rules() -> None:
    summary = json.loads(LIVE_SUMMARY.read_text(encoding="utf-8"))

    assert summary["comparison_row_count"] == 227
    assert summary["numeric_mismatch_count"] == 0
    assert summary["comparison_status_counts"]["MATCH"] == 217
    assert summary["comparison_status_counts"]["LIVE_NO_QUOTA_DATABASE_PRESERVED"] == 4


def test_cwmu_live_values_are_total_only_not_resident_split() -> None:
    rows = _database_by_code()
    row = rows["EA1129"]
    cwmu_rows = [row for row in rows.values() if row["hunt_type"] == "CWMU"]

    assert row["hunt_name"] == "Deseret CWMU"
    assert row["permits_2026_res"] == ""
    assert row["permits_2026_nr"] == ""
    assert row["permits_2026_total"] == "425"
    assert row["permit_allotment_2026_status"] == "LIVE_DWR_CWMU_TOTAL_ONLY_FROM_QUOTA_RES"
    assert len(cwmu_rows) == 283
    assert all(row["permits_2026_res"] == "" and row["permits_2026_nr"] == "" for row in cwmu_rows)
    assert all(row["permits_2026_total"] for row in cwmu_rows)


def test_live_blank_rows_preserve_entered_database_values() -> None:
    row = _database_by_code()["EA1286"]

    assert row["hunt_name"] == "Monroe"
    assert row["permits_2026_res"] == "36"
    assert row["permits_2026_nr"] == "4"
    assert row["permits_2026_total"] == "40"
    assert row["permits_2026_source"] == "2026_RAC_CURRENT_YEAR_ALLOTMENT"


def test_expo_hard_copy_totals_promoted_as_total_only() -> None:
    summary = json.loads(EXPO_SUMMARY.read_text(encoding="utf-8"))
    rows = _database_by_code()

    assert summary["source_row_count"] == 3
    assert summary["promoted_row_count"] == 3
    assert summary["missing_source_codes"] == []

    expected = {"EA1220": "3", "EA1258": "1", "EA1221": "1"}
    for hunt_code, total in expected.items():
        row = rows[hunt_code]
        assert row["permits_2026_res"] == ""
        assert row["permits_2026_nr"] == ""
        assert row["permits_2026_total"] == total
        assert row["permits_2026_source"] == "2026_EXPO_PERMITS_HARD_COPY"
        assert row["permit_allotment_2026_status"] == "HARD_COPY_EXPO_TOTAL_ONLY"


def test_expo_workbook_draw_results_publish_total_only_rows() -> None:
    summary = json.loads(EXPO_TOTAL_ONLY_SUMMARY.read_text(encoding="utf-8"))
    rows = _expo_total_only_rows()
    fieldnames = set(rows[0].keys())

    assert summary["row_count"] == 125
    assert summary["total_expo_permits"] == 200
    assert summary["mapping_status_counts"] == {
        "AMBIGUOUS_DATABASE_MATCH": 47,
        "MATCH_HIGH": 57,
        "NO_DATABASE_MATCH": 21,
    }
    assert "permits_2026_total" in fieldnames
    assert "permits_2026_res" not in fieldnames
    assert "permits_2026_nr" not in fieldnames
    assert all(row["permits_2026_total"] for row in rows)

    assert any(
        row["species"] == "Rocky Mountain Bighorn Sheep"
        and row["sex_type"] == "Ram"
        and row["permits_2026_total"] == "1"
        for row in rows
    )
    assert any(
        row["species"] == "Desert Bighorn Sheep"
        and row["sex_type"] == "Male Only"
        and row["permits_2026_total"] == "1"
        for row in rows
    )


def test_database_sheep_sex_labels_match_dwr_website_shape() -> None:
    summary = json.loads(SHEEP_SUMMARY.read_text(encoding="utf-8"))
    database_rows = _database_by_code()
    sheep_rows = [
        row
        for row in database_rows.values()
        if row["species"] in {"Desert Bighorn Sheep", "Rocky Mountain Bighorn Sheep"}
    ]

    assert summary["sex_type_counts"] == {
        "Desert Bighorn Sheep|Male Only": 25,
        "Rocky Mountain Bighorn Sheep|Ewe": 1,
        "Rocky Mountain Bighorn Sheep|Ram": 20,
    }
    assert {row["sex_type"] for row in sheep_rows if row["species"] == "Desert Bighorn Sheep"} == {"Male Only"}
    assert [row["hunt_code"] for row in sheep_rows if row["sex_type"] == "Ewe"] == ["RE1000"]
    assert all(
        row["sex_type"] == "Ram"
        for row in sheep_rows
        if row["species"] == "Rocky Mountain Bighorn Sheep" and row["hunt_code"] != "RE1000"
    )


def test_reviewed_live_permit_corrections_are_applied() -> None:
    summary = json.loads(REVIEWED_CORRECTIONS_SUMMARY.read_text(encoding="utf-8"))
    rows = _database_by_code()

    assert summary["missing_reviewed_codes"] == []
    assert summary["action_counts"] == {
        "CWMU_TOTAL_ONLY_NORMALIZATION": 283,
        "REVIEWED_NUMERIC_CORRECTION": 8,
    }
    assert summary["cwmu_not_total_only_count"] == 0

    expected = {
        "BI6528": ("6", "0", "6"),
        "BI6532": ("6", "0", "6"),
        "BR7004": ("18", "2", "20"),
        "EB3010": ("10", "1", "11"),
        "EB3047": ("3", "1", "4"),
        "EB3088": ("10", "1", "11"),
        "EB3112": ("2", "0", "2"),
        "EB3185": ("18", "3", "21"),
    }
    for hunt_code, values in expected.items():
        row = rows[hunt_code]
        assert (row["permits_2026_res"], row["permits_2026_nr"], row["permits_2026_total"]) == values
        assert row["permits_2026_source"] == "2026_DWR_HUNT_PLANNER_REVIEWED_LIVE_BLOCK"
        assert row["permit_allotment_2026_status"] == "REVIEWED_LIVE_DWR_SPLIT"


def test_comprehensive_live_dwr_extraction_confirms_broad_database_coverage() -> None:
    summary = json.loads(COMPREHENSIVE_LIVE_SUMMARY.read_text(encoding="utf-8"))

    assert summary["endpoint_count"] == 19
    assert summary["live_unique_hunt_code_count"] == 1389
    assert summary["database_row_count"] == 1394
    assert summary["live_only_count"] == 0
    assert summary["live_numeric_database_blank_count"] == 0
    assert summary["database_only_codes"] == ["BI6505", "BI6506", "BI6529", "BI6536", "BI6539"]
    assert summary["numeric_mismatch_count"] == 0
    assert summary["numeric_mismatch_codes"] == []
    assert summary["comparison_status_counts"]["MATCH"] == 904
    assert summary["comparison_status_counts"]["TOTAL_MATCH_SPLIT_DIFFERS"] == 164
