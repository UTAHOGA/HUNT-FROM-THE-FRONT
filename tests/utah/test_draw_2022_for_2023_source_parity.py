from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "draw_results_truth" / "validation"
SUMMARY = VALIDATION / "draw_2022_for_2023_source_parity_summary.json"
PARITY_CSV = VALIDATION / "draw_2022_for_2023_source_parity.csv"
REPORT_MD = ROOT / "processed_data" / "draw_2022_for_2023_source_parity.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_2022_draw_source_parity_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-draw-2022-for-2023-source-parity.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert PARITY_CSV.exists()
    assert REPORT_MD.exists()


def test_2022_draw_source_pdfs_are_byte_identical_in_active_repo() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    parity_rows = rows(PARITY_CSV)

    assert summary["expected_file_count"] == 15
    assert summary["active_source_file_count"] == 17
    assert summary["byte_match_count"] == 15
    assert summary["review_file_count"] == 0
    assert all(row["status"] == "PASS" for row in parity_rows)


def test_2022_draw_duplicate_aliases_are_recorded_not_counted_as_extra_coverage() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    aliases = summary["active_extra_aliases"]

    assert summary["active_extra_alias_count"] == 2
    assert {alias["alias_status"] for alias in aliases} == {"DUPLICATE_ALIAS_OF_LEGACY_SOURCE"}
    assert summary["active_duplicate_hash_group_count"] == 3


def test_2022_draw_truth_native_count_is_anchored_and_source_label_flagged() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["model_target_year"] == "2023"
    assert summary["source_draw_result_year"] == "2022"
    assert summary["draw_truth_2022_rows"] == 18688
    assert summary["draw_truth_2022_unique_hunt_codes"] == 1024
    assert summary["draw_truth_source_label_status"] == "SOURCE_LABEL_LINEAGE_REVIEW"
