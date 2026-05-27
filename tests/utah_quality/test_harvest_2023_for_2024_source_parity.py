from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "harvest_results_truth" / "validation"
SUMMARY = VALIDATION / "harvest_2023_for_2024_source_parity_summary.json"
PARITY_CSV = VALIDATION / "harvest_2023_for_2024_source_parity.csv"
REPORT_MD = ROOT / "processed_data" / "harvest_2023_for_2024_source_parity.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_2023_for_2024_harvest_source_parity_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-harvest-2023-for-2024-source-parity.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert PARITY_CSV.exists()
    assert REPORT_MD.exists()


def test_2023_for_2024_promoted_baseline_and_turkey_packages_match_by_content() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    parity_rows = rows(PARITY_CSV)

    assert summary["source_file_count"] == 50
    assert summary["content_match_count"] == 19
    assert summary["byte_match_count"] == 0
    assert summary["missing_active_package_copy_count"] == 31
    assert summary["baseline_source_file_count"] == 15
    assert summary["baseline_content_match_count"] == 15
    assert summary["turkey_source_file_count"] == 4
    assert summary["turkey_content_match_count"] == 4

    baseline_rows = [row for row in parity_rows if row["source_group"] == "2023_FOR_2024_ALL_SPECIES_BASELINE"]
    turkey_rows = [row for row in parity_rows if row["source_group"] == "2023_24_TURKEY_FOR_2025_SEPARATE_PACKAGE"]
    assert all(row["status"] == "PASS_ACTIVE_PACKAGE_CONTENT_MATCH" for row in baseline_rows)
    assert all(row["status"] == "PASS_ACTIVE_PACKAGE_CONTENT_MATCH" for row in turkey_rows)


def test_2023_for_2024_harvest_and_draw_same_year_counts_are_anchored() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    same_year = summary["same_year_2023"]

    assert summary["normalized_2023_best_rows"] == 1078
    assert summary["normalized_2023_unique_hunt_codes"] == 1078
    assert same_year["harvest_native_unique_hunt_codes"] == "1078"
    assert same_year["draw_native_unique_hunt_codes"] == "1010"
    assert same_year["same_year_overlap_hunt_codes"] == "921"
    assert same_year["harvest_only_hunt_codes"] == "157"
    assert same_year["draw_only_hunt_codes"] == "89"


def test_2023_existing_complete_harvest_vs_draw_artifact_is_registered() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    existing = summary["existing_complete_2023_harvest_vs_draw_comparison"]

    assert existing["harvest_files_checked"] == 50
    assert existing["complete_harvest_hunt_codes"] == 1085
    assert existing["draw_odds_hunt_codes"] == 984
    assert existing["both_harvest_and_draw"] == 971
