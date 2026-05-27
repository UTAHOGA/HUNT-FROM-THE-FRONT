from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "draw_results_truth" / "validation"
SUMMARY = VALIDATION / "draw_2023_moose_pdf_sources_summary.json"
SOURCE_AUDIT = VALIDATION / "draw_2023_moose_pdf_sources.csv"
CODE_AUDIT = VALIDATION / "draw_2023_moose_pdf_hunt_codes.csv"
REPORT = ROOT / "processed_data" / "draw_2023_moose_pdf_sources.md"
ACTIVE_PDF_DIR = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2024" / "pdf" / "draw_odds"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_2023_moose_pdf_source_audit_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-draw-2023-moose-pdf-sources.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert SOURCE_AUDIT.exists()
    assert CODE_AUDIT.exists()
    assert REPORT.exists()


def test_2023_moose_pdf_sources_are_present_and_byte_anchored() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert (ACTIVE_PDF_DIR / "bull moose.pdf").exists()
    assert (ACTIVE_PDF_DIR / "antlerless moose.pdf").exists()
    assert summary["status"] == "PASS"
    assert summary["source_pdf_count"] == 2
    assert summary["byte_match_count"] == 2
    assert summary["review_source_count"] == 0


def test_2023_moose_pdf_hunt_code_counts_and_csv_linkage_are_locked() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    by_file = {row["source_file"]: row for row in summary["source_summaries"]}

    assert summary["total_pdf_hunt_codes"] == 33
    assert summary["codes_matched_to_expected_csv"] == 33
    assert summary["codes_matched_to_harvest_draw_comparison"] == 33

    bull = by_file["bull moose.pdf"]
    assert bull["pdf_page_count"] == "41"
    assert bull["pdf_unique_hunt_codes"] == "30"
    assert bull["expected_csv"] == "draw_results_2023_for_2024_long.csv"
    assert bull["expected_csv_rows_matching_codes"] == "1860"
    assert bull["expected_csv_source_label_counts_json"] == '{"23_bg-odds.pdf": 1860}'

    antlerless = by_file["antlerless moose.pdf"]
    assert antlerless["pdf_page_count"] == "3"
    assert antlerless["pdf_unique_hunt_codes"] == "3"
    assert antlerless["expected_csv"] == "draw_results_2023_for_2024_UPLOADED_COMBINED_long.csv"
    assert antlerless["expected_csv_rows_matching_codes"] == "108"
    assert antlerless["expected_csv_source_label_counts_json"] == '{"2023 Antlerless big game draw results.pdf": 108}'


def test_2023_moose_harvest_draw_buckets_are_recorded() -> None:
    source_rows = {row["source_file"]: row for row in rows(SOURCE_AUDIT)}
    code_rows = rows(CODE_AUDIT)

    assert source_rows["bull moose.pdf"]["comparison_bucket_counts_json"] == '{"both": 29, "draw_only": 1}'
    assert source_rows["bull moose.pdf"]["active_database_2026_counts_json"] == '{"NO": 9, "YES": 21}'
    assert source_rows["antlerless moose.pdf"]["comparison_bucket_counts_json"] == '{"both": 3}'
    assert source_rows["antlerless moose.pdf"]["active_database_2026_counts_json"] == '{"NO": 2, "YES": 1}'

    draw_only = [row for row in code_rows if row["comparison_bucket"] == "draw_only"]
    assert len(draw_only) == 1
    assert draw_only[0]["hunt_code"] == "MB6252"
    assert draw_only[0]["source_file"] == "bull moose.pdf"


def test_2023_moose_code_level_species_and_sex_are_mapped() -> None:
    code_rows = rows(CODE_AUDIT)
    by_file = {}
    for row in code_rows:
        by_file.setdefault(row["source_file"], set()).add((row["species"], row["sex_type"]))

    assert by_file["bull moose.pdf"] == {("Moose", "Male Only")}
    assert by_file["antlerless moose.pdf"] == {("Moose", "Antlerless")}
