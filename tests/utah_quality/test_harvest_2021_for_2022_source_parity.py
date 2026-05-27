from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "harvest_results_truth" / "validation"
SUMMARY = VALIDATION / "harvest_2021_for_2022_source_parity_summary.json"
PARITY_CSV = VALIDATION / "harvest_2021_for_2022_source_parity.csv"
REPORT_MD = ROOT / "processed_data" / "harvest_2021_for_2022_source_parity.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_2021_for_2022_harvest_source_parity_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-harvest-2021-for-2022-source-parity.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert PARITY_CSV.exists()
    assert REPORT_MD.exists()


def test_2021_for_2022_harvest_source_files_match_active_package_by_content() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    parity_rows = rows(PARITY_CSV)

    assert summary["expected_file_count"] == 15
    assert summary["content_match_count"] == 15
    assert summary["review_file_count"] == 0
    assert all(row["status"] == "PASS" for row in parity_rows)
    assert all(row["fields_match"] == "YES" for row in parity_rows)
    assert all(row["row_content_match"] == "YES" for row in parity_rows)


def test_2021_for_2022_harvest_normalized_year_counts_are_anchored() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["normalized_2021_best_rows"] == 974
    assert summary["normalized_2021_unique_hunt_codes"] == 974
