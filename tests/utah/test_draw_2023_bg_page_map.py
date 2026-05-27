from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "draw_results_truth" / "validation"
SUMMARY = VALIDATION / "draw_2023_bg_page_map_summary.json"
PAGE_MAP = VALIDATION / "draw_2023_bg_page_map.csv"
REPORT = ROOT / "processed_data" / "draw_2023_bg_page_map.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_2023_bg_page_map_audit_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-draw-2023-bg-page-map.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert PAGE_MAP.exists()
    assert REPORT.exists()


def test_2023_bg_pdf_and_extraction_shape_are_anchored() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["status"] == "PASS"
    assert summary["legacy_active_pdf_byte_match"] is True
    assert summary["pdf_page_count"] == 588
    assert summary["source_csv_row_count"] == 35960
    assert summary["source_csv_unique_hunt_codes"] == 580
    assert summary["source_pdf_page_min"] == 2
    assert summary["source_pdf_page_max"] == 588


def test_2023_bg_user_supplied_map_is_preserved_but_not_forced() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    page_rows = rows(PAGE_MAP)
    user_rows = [row for row in page_rows if row["page_map_type"] == "user_supplied_pdf_page_map"]

    assert [(row["page_start"], row["page_end"]) for row in user_rows] == [
        ("1", "1"),
        ("2", "206"),
        ("208", "365"),
        ("367", "434"),
        ("436", "567"),
        ("568", "588"),
    ]
    assert summary["user_supplied_page_map_rows_assigned"] == 35774
    assert summary["unassigned_rows_by_user_supplied_map"] == 186


def test_2023_bg_observed_pdf_page_map_covers_every_extracted_row() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    page_rows = rows(PAGE_MAP)
    observed = {
        row["section_id"]: row
        for row in page_rows
        if row["page_map_type"] == "observed_extraction_pdf_page_map"
    }

    assert summary["observed_extraction_page_map_rows_assigned"] == 35960
    assert summary["unassigned_rows_by_observed_map"] == 0
    assert observed["OBSERVED_LIMITED_ENTRY_DEER"]["extracted_rows"] == "11718"
    assert observed["OBSERVED_LIMITED_ENTRY_DEER"]["unique_hunt_codes"] == "189"
    assert observed["OBSERVED_LIMITED_ENTRY_ELK"]["extracted_rows"] == "8804"
    assert observed["OBSERVED_ANY_BULL_ELK_CWMU"]["extracted_rows"] == "4278"
    assert observed["OBSERVED_LIMITED_ENTRY_BUCK_PRONGHORN"]["extracted_rows"] == "5332"
    assert observed["OBSERVED_ONCE_IN_A_LIFETIME"]["extracted_rows"] == "5828"


def test_2023_bg_harvest_draw_comparison_linkage_is_recorded() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    linkage = summary["harvest_draw_comparison_linkage"]

    assert linkage["source_hunt_codes"] == 580
    assert linkage["matched_comparison_hunt_codes"] == 580
    assert linkage["missing_from_comparison_hunt_codes"] == []
    assert linkage["comparison_bucket_counts"] == {"both": 579, "draw_only": 1}
    assert linkage["draw_only_hunt_codes"] == ["MB6252"]
    assert linkage["active_database_2026_counts"] == {"NO": 39, "YES": 541}
