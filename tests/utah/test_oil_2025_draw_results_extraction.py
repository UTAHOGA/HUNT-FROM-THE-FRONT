import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/extract-oil-2025-draw-results-permits.py"
NORMALIZED = ROOT / "data_truth/draw_results_truth/normalized/oil_2025_draw_results_model_target_2026_permit_totals.csv"
VALIDATION = ROOT / "data_truth/draw_results_truth/validation/oil_2025_draw_results_model_target_2026_vs_DATABASE.csv"
SUMMARY = ROOT / "data_truth/draw_results_truth/validation/oil_2025_draw_results_model_target_2026_summary.json"


def run_script() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def by_code(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["hunt_code"]: row for row in rows}


def test_oil_2025_pdf_extracts_all_pages_and_prefix_counts() -> None:
    run_script()
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    rows = read_csv(NORMALIZED)

    assert summary["pdf_pages"] == 101
    assert summary["source_rows"] == 101
    assert summary["unique_hunt_codes"] == 101
    assert len(rows) == 101
    assert summary["prefix_counts"] == {"BI": 15, "DS": 18, "GO": 17, "MB": 36, "RS": 15}


def test_oil_2025_key_hunt_totals_are_extracted_correctly() -> None:
    run_script()
    lookup = by_code(read_csv(NORMALIZED))

    assert lookup["MB6000"]["resident_total_permits"] == "12"
    assert lookup["MB6000"]["nonresident_total_permits"] == "3"
    assert lookup["MB6000"]["total_public_draw_permits"] == "15"
    assert lookup["BI6537"]["resident_total_permits"] == "5"
    assert lookup["BI6537"]["nonresident_total_permits"] == "5"
    assert lookup["DS6601"]["resident_total_permits"] == "9"
    assert lookup["DS6601"]["nonresident_total_permits"] == "2"
    assert lookup["DS6601"]["total_public_draw_permits"] == "11"
    assert lookup["GO6800"]["total_public_draw_permits"] == "8"
    assert lookup["RS6726"]["resident_total_permits"] == "4"
    assert lookup["RS6726"]["nonresident_total_permits"] == "1"
    assert lookup["RS6726"]["sex_type"] == "Ram"


def test_oil_2025_extraction_carries_mapping_law_columns() -> None:
    run_script()
    rows = read_csv(NORMALIZED)

    for required in [
        "hunt_code",
        "boundary_id",
        "hunt_code_mapping_status",
        "boundary_id_mapping_status",
        "candidate_hunt_code",
        "candidate_boundary_id",
    ]:
        assert required in rows[0]
    assert not [row for row in rows if not row["hunt_code"]]
    status_counts = {}
    for row in rows:
        status_counts[row["hunt_code_mapping_status"]] = status_counts.get(row["hunt_code_mapping_status"], 0) + 1
    assert status_counts == {"REVIEWED_CURRENT_HUNT_CODE": 89, "SOURCE_CODE_NOT_IN_DATABASE": 12}


def test_oil_2025_database_comparison_uses_draw_result_fields() -> None:
    run_script()
    rows = read_csv(VALIDATION)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert len(rows) == 101
    assert summary["database_missing_codes"] == 12
    assert summary["database_missing_hunt_codes"] == [
        "MB6200",
        "MB6207",
        "MB6209",
        "MB6217",
        "MB6220",
        "MB6223",
        "MB6224",
        "MB6225",
        "MB6240",
        "MB6254",
        "MB6257",
        "MB6259",
    ]
    assert summary["database_blank_count"] == 0
    assert summary["database_difference_count"] == 0
    assert summary["database_match_count"] == 89
    assert {row["database_comparison_status"] for row in rows} == {
        "MATCH_DATABASE_2025_DRAW_PERMITS",
        "MISSING_DATABASE_ROW",
    }
