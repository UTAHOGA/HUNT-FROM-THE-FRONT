from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "draw_results_truth" / "validation"
SUMMARY = VALIDATION / "draw_2023_for_2024_pdf_source_parity_summary.json"
PARITY_CSV = VALIDATION / "draw_2023_for_2024_pdf_source_parity.csv"
REPORT_MD = ROOT / "processed_data" / "draw_2023_for_2024_pdf_source_parity.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_2023_for_2024_draw_pdf_source_parity_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-draw-2023-for-2024-pdf-source-parity.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert PARITY_CSV.exists()
    assert REPORT_MD.exists()


def test_2023_for_2024_draw_pdfs_are_byte_identical_in_active_repo() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    parity_rows = rows(PARITY_CSV)

    assert summary["expected_file_count"] == 17
    assert summary["active_source_file_count"] == 17
    assert summary["byte_match_count"] == 17
    assert summary["review_file_count"] == 0
    assert summary["active_only_source_file_count"] == 0
    assert summary["active_duplicate_hash_group_count"] == 0
    assert all(row["status"] == "PASS" for row in parity_rows)


def test_2023_for_2024_pdf_labels_are_partially_represented_in_csv_exports() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    coverage = summary["csv_source_label_summary"]["combined_csv_pdf_label_coverage"]

    assert coverage["expected_pdf_count"] == 17
    assert coverage["represented_expected_pdf_count"] == 7
    assert coverage["csv_source_labels_not_in_expected_pdf_set"] == []
    assert len(coverage["expected_pdf_labels_not_represented_by_any_csv"]) == 10


def test_2023_for_2024_normalized_draw_truth_source_labels_need_lineage_review() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    normalized = summary["normalized_draw_truth_source_summary"]

    assert normalized["normalized_rows"] == 37128
    assert normalized["normalized_unique_hunt_codes"] == 580
    assert normalized["normalized_source_file_count"] == 4
    assert normalized["normalized_source_labels_matching_expected_pdf_set"] == []
    assert len(normalized["normalized_source_labels_not_in_expected_pdf_set"]) == 4
    assert normalized["source_label_status"] == "SOURCE_LABEL_LINEAGE_REVIEW"
