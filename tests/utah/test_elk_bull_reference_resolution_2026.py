import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_elk_bull_reference_rows_are_non_modeled_and_preserve_total_only_values():
    predictive = read_rows(ROOT / "processed_data/draw_reality_engine_predictive_v2.csv")
    reference_rows = [
        row
        for row in predictive
        if row.get("model_version") == "elk_bull_reference_v1.0.0"
    ]
    by_code = {row["hunt_code"]: row for row in reference_rows}

    assert set(by_code) == {
        "EB1001",
        "EB1002",
        "EB1003",
        "EB1004",
        "EB1005",
        "EB1009",
        "EB1010",
        "EB1012",
        "EB3128",
        "EB3209",
    }
    assert {row["species"] for row in reference_rows} == {"Elk"}
    assert {row["sex_type"] for row in reference_rows} == {"Bull"}
    assert {row["modeled_by_engine"] for row in reference_rows} == {"False"}
    assert {row["probability_model"] for row in reference_rows} == {"NONE"}
    assert {row["display_odds_text"] for row in reference_rows} == {
        "Elk bull reference only; odds not modeled"
    }

    assert by_code["EB1012"]["permit_allotment_2026_total"] == "500"
    assert by_code["EB3128"]["permit_allotment_2026_total"] == "1"
    assert by_code["EB3209"]["permit_allotment_2026_total"] == "1"
    assert by_code["EB1012"]["permit_allotment_2026_status"] == "TOTAL_ONLY"
    assert by_code["EB3128"]["permit_allotment_2026_status"] == "TOTAL_ONLY"
    assert by_code["EB3209"]["permit_allotment_2026_status"] == "TOTAL_ONLY"

    no_quota_codes = {"EB1001", "EB1002", "EB1003", "EB1004", "EB1005", "EB1009", "EB1010"}
    assert all(by_code[code]["permit_allotment_2026_status"] == "NO_QUOTA_PUBLISHED" for code in no_quota_codes)
    assert all(not by_code[code]["permit_allotment_2026_total"] for code in no_quota_codes)
    assert all(not by_code[code]["quota_2026_total"] for code in no_quota_codes)
    assert all(not by_code[code]["public_permits_2026"] for code in no_quota_codes)


def test_elk_bull_reference_reconciliation_summary_is_clean():
    summary = json.loads(
        (ROOT / "processed_data/2026_elk_bull_reference_hunt_code_reconciliation_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["classification"] == "ELK_BULL_REFERENCE_HUNT_CODE_RECONCILIATION"
    assert summary["blockers"] == 0
    assert summary["source_reference_code_count"] == 13
    assert summary["permit_status_counts"] == {"NO_QUOTA_PUBLISHED": 8, "TOTAL_ONLY": 5}
    assert summary["promotion_summary"]["newly_promoted_hunt_code_count"] == 10
    assert summary["promotion_summary"]["still_missing_predictive_hunt_code_count"] == 0
    assert summary["promotion_summary"]["stale_database_total_leak_count"] == 0
    assert summary["promotion_summary"]["total_only_source_hunt_codes"] == [
        "EB1000",
        "EB1007",
        "EB1012",
        "EB3128",
        "EB3209",
    ]


def test_elk_bull_reference_spreadsheet_export_is_complete():
    csv_path = ROOT / "processed_data/elk_bull_reference_hunt_planner_reference.csv"
    xlsx_path = ROOT / "processed_data/elk_bull_reference_hunt_planner_reference.xlsx"
    report = json.loads(
        (ROOT / "processed_data/elk_bull_reference_hunt_planner_reference_report.json").read_text(
            encoding="utf-8"
        )
    )
    rows = read_rows(csv_path)

    assert csv_path.exists()
    assert xlsx_path.exists()
    assert report["status"] == "PASS"
    assert report["row_count"] == 13
    assert report["total_only_row_count"] == 5
    assert report["no_quota_published_row_count"] == 8
    assert report["stale_quota_leak_count"] == 0
    assert {"Non Res", "Res", "Total"}.issubset(rows[0])
    assert {row["Hunt Code"] for row in rows} == set(report["total_only_codes"]) | set(report["no_quota_published_codes"])


def test_elk_bull_reference_gap_scan_is_resolved():
    gap_rows = read_rows(ROOT / "processed_data/2026_hunt_code_family_gap_scan.csv")
    by_prefix = {row["code_prefix"]: row for row in gap_rows}
    assert by_prefix["EB"]["status"] == "RESOLVED"
    assert by_prefix["EB"]["database_code_count"] == "222"
    assert by_prefix["EB"]["missing_predictive_v2_count"] == "0"

    summary = json.loads(
        (ROOT / "processed_data/2026_hunt_code_family_gap_scan_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["total_missing_predictive_v2_current_database_codes"] == 0
    assert "EB" in summary["resolved_families"]
