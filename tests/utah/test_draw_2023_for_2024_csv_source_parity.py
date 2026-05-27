from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "draw_results_truth" / "validation"
SUMMARY = VALIDATION / "draw_2023_for_2024_csv_source_parity_summary.json"
PARITY_CSV = VALIDATION / "draw_2023_for_2024_csv_source_parity.csv"
REPORT_MD = ROOT / "processed_data" / "draw_2023_for_2024_csv_source_parity.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_2023_for_2024_draw_csv_source_parity_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-draw-2023-for-2024-csv-source-parity.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert PARITY_CSV.exists()
    assert REPORT_MD.exists()


def test_2023_for_2024_draw_csvs_are_byte_identical_in_active_repo() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    parity_rows = rows(PARITY_CSV)

    assert summary["expected_file_count"] == 2
    assert summary["byte_match_count"] == 2
    assert summary["row_content_match_count"] == 2
    assert summary["review_file_count"] == 0
    assert all(row["status"] == "PASS" for row in parity_rows)


def test_2023_for_2024_draw_csv_file_shapes_are_anchored() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    standard = summary["source_file_summaries"]["draw_results_2023_for_2024_long.csv"]
    combined = summary["source_file_summaries"]["draw_results_2023_for_2024_UPLOADED_COMBINED_long.csv"]

    assert standard["row_count"] == 35960
    assert standard["unique_hunt_codes"] == 580
    assert standard["source_file_count"] == 1
    assert standard["draw_method_counts"] == {"bonus": 35960}

    assert combined["row_count"] == 38682
    assert combined["unique_hunt_codes"] == 593
    assert combined["source_file_count"] == 6
    assert combined["draw_method_counts"] == {"bonus": 16086, "preference": 22596}


def test_2023_for_2024_draw_csv_relationship_and_normalized_overlap_are_recorded() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["source_file_relationship"] == {
        "row_key_overlap": 11718,
        "standard_only_row_keys": 24242,
        "combined_only_row_keys": 26964,
    }
    assert summary["normalized_model_year_2024_summary"]["rows"] == 37128
    assert summary["normalized_model_year_2024_summary"]["unique_hunt_codes"] == 580
    assert summary["standard_vs_normalized_2024"]["hunt_code_overlap"] == 558
    assert summary["standard_vs_normalized_2024"]["row_key_overlap"] == 21416
    assert summary["combined_vs_normalized_2024"]["hunt_code_overlap"] == 181
    assert summary["combined_vs_normalized_2024"]["row_key_overlap"] == 8011


def test_2023_for_2024_sources_are_not_confused_with_normalized_draw_year_2023() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["source_draw_result_year"] == "2023"
    assert summary["model_target_year"] == "2024"
    assert summary["normalized_draw_year_2023_summary"]["rows"] == 17128
    assert summary["normalized_draw_year_2023_summary"]["unique_hunt_codes"] == 1010
    assert summary["standard_vs_normalized_2023"]["row_key_overlap"] == 0
    assert summary["combined_vs_normalized_2023"]["row_key_overlap"] == 0
