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


def _database_by_code() -> dict[str, dict[str, str]]:
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        return {row["hunt_code"]: row for row in csv.DictReader(handle)}


def test_live_dwr_comparison_has_no_numeric_mismatches_after_shape_rules() -> None:
    summary = json.loads(LIVE_SUMMARY.read_text(encoding="utf-8"))

    assert summary["comparison_row_count"] == 227
    assert summary["numeric_mismatch_count"] == 0
    assert summary["comparison_status_counts"]["MATCH"] == 217
    assert summary["comparison_status_counts"]["LIVE_NO_QUOTA_DATABASE_PRESERVED"] == 4


def test_cwmu_live_values_are_total_only_not_resident_split() -> None:
    row = _database_by_code()["EA1129"]

    assert row["hunt_name"] == "Deseret CWMU"
    assert row["permits_2026_res"] == ""
    assert row["permits_2026_nr"] == ""
    assert row["permits_2026_total"] == "425"
    assert row["permit_allotment_2026_status"] == "LIVE_DWR_CWMU_TOTAL_ONLY_FROM_QUOTA_RES"


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


def test_comprehensive_live_dwr_extraction_confirms_broad_database_coverage() -> None:
    summary = json.loads(COMPREHENSIVE_LIVE_SUMMARY.read_text(encoding="utf-8"))

    assert summary["endpoint_count"] == 19
    assert summary["live_unique_hunt_code_count"] == 1389
    assert summary["database_row_count"] == 1394
    assert summary["live_only_count"] == 0
    assert summary["live_numeric_database_blank_count"] == 0
    assert summary["database_only_codes"] == ["BI6505", "BI6506", "BI6529", "BI6536", "BI6539"]
    assert summary["numeric_mismatch_codes"] == [
        "BI6528",
        "BI6532",
        "BR7004",
        "EB3010",
        "EB3047",
        "EB3088",
        "EB3112",
        "EB3185",
    ]
    assert summary["comparison_status_counts"]["MATCH"] == 682
    assert summary["comparison_status_counts"]["TOTAL_MATCH_SPLIT_DIFFERS"] == 378
