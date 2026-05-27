from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "draw_results_truth" / "validation"
SUMMARY = VALIDATION / "draw_2020_hashed_for_2021_source_parity_summary.json"
PARITY_CSV = VALIDATION / "draw_2020_hashed_for_2021_source_parity.csv"
REPORT_MD = ROOT / "processed_data" / "draw_2020_hashed_for_2021_source_parity.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_2020_hashed_draw_source_parity_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-draw-2020-hashed-for-2021-source-parity.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert PARITY_CSV.exists()
    assert REPORT_MD.exists()


def test_2020_hashed_draw_pdfs_are_byte_identical_in_active_repo() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    parity_rows = rows(PARITY_CSV)

    assert summary["expected_file_count"] == 13
    assert summary["active_source_file_count"] == 13
    assert summary["byte_match_count"] == 13
    assert summary["review_file_count"] == 0
    assert summary["active_only_source_file_count"] == 0
    assert summary["active_duplicate_hash_group_count"] == 0
    assert all(row["status"] == "PASS" for row in parity_rows)


def test_2020_hashed_draw_source_overlap_with_named_20_star_package_is_recorded() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["same_hash_named_2020_source_match_count"] == 10
    assert summary["hashed_sources_without_named_2020_match_count"] == 3
    assert set(summary["hashed_sources_without_named_2020_match"]) == {
        "5213601e__turkey_2020_turkey_bonus_points_draw_results.pdf",
        "68991b97__turkey_2020_youth_turkey_draw_results.pdf",
        "dff7fc92__cougar_Drawing odds.pdf",
    }


def test_2020_hashed_draw_truth_anchor_is_lineage_review_only() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["source_draw_result_year"] == "2020"
    assert summary["model_target_year"] == "2021"
    assert summary["draw_truth_2020_rows"] == 0
    assert summary["draw_truth_2021_rows"] == 27519
    assert summary["draw_truth_2021_unique_hunt_codes"] == 550
    assert summary["draw_truth_2021_source_files"] == ["21_bg-odds.pdf"]
    assert summary["draw_truth_source_label_status"] == "SOURCE_LABEL_LINEAGE_REVIEW"
