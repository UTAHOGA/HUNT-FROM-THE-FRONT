import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PRIVATE_LAND_CODES = {"LP5025", "LP5031", "LP5033", "LP5046", "LP5049", "LP5051"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_pronghorn_export_contains_public_pb_and_blank_private_lp_quotas():
    rows = read_rows(ROOT / "processed_data/pronghorn_buck_limited_entry_reference_export.csv")
    assert len(rows) == 94
    assert sum(1 for row in rows if row["Hunt Code"].startswith("PB")) == 88
    assert sum(1 for row in rows if row["Hunt Code"].startswith("LP")) == 6

    by_code = {row["Hunt Code"]: row for row in rows}
    assert by_code["PB5025"]["Non Res"] == "5"
    assert by_code["PB5025"]["Res"] == "43"
    assert by_code["PB5025"]["Total"] == "48"

    for code in PRIVATE_LAND_CODES:
        assert by_code[code]["Non Res"] == ""
        assert by_code[code]["Res"] == ""
        assert by_code[code]["Total"] == ""
        assert by_code[code]["Permit Status"] == "NO_QUOTA_PUBLISHED"
        assert by_code[code]["Data Status"] == "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED"


def test_private_land_pronghorn_rows_are_non_modeled_reference_rows():
    rows = read_rows(ROOT / "processed_data/draw_reality_engine_predictive_v2.csv")
    by_code = {
        row["hunt_code"]: row
        for row in rows
        if row.get("hunt_code") in PRIVATE_LAND_CODES
        and row.get("model_version") == "pronghorn_private_land_reference_v1.0.0"
    }
    assert set(by_code) == PRIVATE_LAND_CODES

    for row in by_code.values():
        assert row["modeled_by_engine"] == "False"
        assert row["probability_model"] == "NONE"
        assert row["draw_pool"] == "private_land_pronghorn_reference"
        assert row["residency"] == "Private Land Only"
        assert row["permit_allotment_2026_status"] == "NO_QUOTA_PUBLISHED"
        assert row["permit_allotment_2026_res"] == ""
        assert row["permit_allotment_2026_nr"] == ""
        assert row["permit_allotment_2026_total"] == ""
        assert row["private_land_only_flag"] == "True"


def test_pronghorn_resolution_reports_and_gap_scan_are_clean():
    summary = json.loads(
        (ROOT / "processed_data/2026_pronghorn_hunt_code_reconciliation_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["blockers"] == 0
    assert summary["current_database_prefix_counts"] == {"LP": 6, "PB": 88}
    assert summary["promotion_summary"]["still_missing_predictive_hunt_code_count"] == 0
    assert summary["promotion_summary"]["quota_leak_reference_row_count"] == 0

    gap_rows = read_rows(ROOT / "processed_data/2026_hunt_code_family_gap_scan.csv")
    by_prefix = {row["code_prefix"]: row for row in gap_rows}
    assert by_prefix["PB"]["status"] == "RESOLVED"
    assert by_prefix["LP"]["status"] == "RESOLVED"
    assert by_prefix["LP"]["missing_predictive_v2_count"] == "0"
