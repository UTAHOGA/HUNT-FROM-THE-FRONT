import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_elk_private_land_reference_rows_are_non_modeled_and_no_quota():
    predictive = read_rows(ROOT / "processed_data/draw_reality_engine_predictive_v2.csv")
    reference_rows = [
        row
        for row in predictive
        if row.get("model_version") == "elk_private_land_reference_v1.0.0"
    ]
    assert len(reference_rows) == 126
    assert {row["hunt_code"][:2] for row in reference_rows} == {"EL"}
    assert {row["species"] for row in reference_rows} == {"Elk"}
    assert {row["sex_type"] for row in reference_rows} == {"Bull"}
    assert {row["modeled_by_engine"] for row in reference_rows} == {"False"}
    assert {row["probability_model"] for row in reference_rows} == {"NONE"}
    assert {row["draw_pool"] for row in reference_rows} == {"private_land_elk_reference"}
    assert {row["residency"] for row in reference_rows} == {"Private Land Only"}
    assert {row["permit_allotment_2026_status"] for row in reference_rows} == {"NO_QUOTA_PUBLISHED"}
    assert {row["display_odds_text"] for row in reference_rows} == {
        "Private-land elk reference only; odds not modeled"
    }
    assert all(not row["permit_allotment_2026_res"] for row in reference_rows)
    assert all(not row["permit_allotment_2026_nr"] for row in reference_rows)
    assert all(not row["permit_allotment_2026_total"] for row in reference_rows)
    assert all(row["private_land_only_flag"] == "True" for row in reference_rows)


def test_elk_private_land_reconciliation_summary_is_clean():
    summary = json.loads(
        (ROOT / "processed_data/2026_elk_private_land_hunt_code_reconciliation_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["classification"] == "ELK_PRIVATE_LAND_HUNT_CODE_RECONCILIATION"
    assert summary["blockers"] == 0
    assert summary["current_database_code_count"] == 126
    assert summary["promotion_summary"]["newly_promoted_hunt_code_count"] == 126
    assert summary["promotion_summary"]["still_missing_predictive_hunt_code_count"] == 0
    assert summary["promotion_summary"]["quota_leak_reference_row_count"] == 0
    assert summary["lo_elk_rows_not_promoted_by_this_resolver"] == [
        "LO0011",
        "LO0012",
        "LO0013",
        "LO0014",
        "LO0015",
    ]


def test_elk_private_land_gap_scan_is_resolved():
    gap_rows = read_rows(ROOT / "processed_data/2026_hunt_code_family_gap_scan.csv")
    by_prefix = {row["code_prefix"]: row for row in gap_rows}
    assert by_prefix["EL"]["status"] == "RESOLVED"
    assert by_prefix["EL"]["database_code_count"] == "126"
    assert by_prefix["EL"]["predictive_v2_code_count"] == "126"
    assert by_prefix["EL"]["missing_predictive_v2_count"] == "0"

    summary = json.loads(
        (ROOT / "processed_data/2026_hunt_code_family_gap_scan_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["total_missing_predictive_v2_current_database_codes"] == 14
    assert "EL" in summary["resolved_families"]
