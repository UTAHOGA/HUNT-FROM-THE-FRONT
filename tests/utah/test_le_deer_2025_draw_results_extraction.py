import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/extract-le-deer-2025-draw-results-permits.py"
NORMALIZED = ROOT / "data_truth/draw_results_truth/normalized/le_deer_2025_draw_results_model_target_2026_permit_totals.csv"
VALIDATION = ROOT / "data_truth/draw_results_truth/validation/le_deer_2025_draw_results_model_target_2026_vs_DATABASE.csv"
SUMMARY = ROOT / "data_truth/draw_results_truth/validation/le_deer_2025_draw_results_model_target_2026_summary.json"


def run_script() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def by_code(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["hunt_code"]: row for row in rows}


def test_le_deer_pdf_extracts_one_row_per_hunt_page() -> None:
    run_script()
    rows = read_csv(NORMALIZED)
    lookup = by_code(rows)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert len(rows) == 195
    assert len(lookup) == 195
    assert summary["pdf_pages"] == 196
    assert summary["reported_draw_year"] == 2025
    assert summary["model_target_year"] == 2026
    assert lookup["DB1000"]["resident_total_permits"] == "8"
    assert lookup["DB1000"]["nonresident_total_permits"] == "1"
    assert lookup["DB1001"]["resident_total_permits"] == "25"
    assert lookup["DB1001"]["nonresident_total_permits"] == "3"
    assert lookup["DB1349"]["total_public_draw_permits"] == "9"
    assert summary["source_total_public_draw_permits"] == 1714


def test_le_deer_draw_results_carry_mapping_law_columns() -> None:
    run_script()
    rows = read_csv(NORMALIZED)

    assert rows
    for required in [
        "hunt_code",
        "boundary_id",
        "hunt_code_mapping_status",
        "boundary_id_mapping_status",
        "candidate_hunt_code",
        "candidate_boundary_id",
    ]:
        assert required in rows[0]
    assert {row["hunt_code_mapping_status"] for row in rows} == {"REVIEWED_CURRENT_HUNT_CODE"}


def test_le_deer_draw_results_match_database_or_flag_missing_rows_only() -> None:
    run_script()
    validation = read_csv(VALIDATION)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["database_match_count"] == 195
    assert summary["database_difference_count"] == 0
    assert summary["missing_database_row_count"] == 0
    assert summary["missing_database_codes"] == []
    assert {row["database_comparison_status"] for row in validation} == {"MATCH_DATABASE_2025_DRAW_FIELDS"}
