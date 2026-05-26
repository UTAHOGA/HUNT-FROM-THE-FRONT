import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/normalize-desert-bighorn-permits-2026.py"
REVIEWED_EXPORT = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 desert bighorn reviewed res-nr-total.csv"
NORMALIZED = ROOT / "data_truth/permit_overlay_truth/normalized/desert_bighorn_permits_2026_canonical.csv"
DB_COMPARE = ROOT / "data_truth/permit_overlay_truth/validation/desert_bighorn_permits_2026_vs_DATABASE.csv"
RAC_COMPARE = ROOT / "data_truth/permit_overlay_truth/validation/desert_bighorn_permits_2026_vs_RAC.csv"
PARALLEL = ROOT / "data_truth/permit_overlay_truth/validation/desert_bighorn_public_vs_conservation_parallel_2026.csv"
SUMMARY = ROOT / "data_truth/permit_overlay_truth/validation/desert_bighorn_permits_2026_summary.json"


def run_script() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def by_code(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["hunt_code"]: row for row in rows}


def test_desert_bighorn_public_oial_source_is_normalized_to_one_row_per_code() -> None:
    run_script()
    rows = read_csv(NORMALIZED)
    lookup = by_code(rows)

    assert len(rows) == 18
    assert len(lookup) == 18
    assert lookup["DS6601"]["permits_2026_res"] == "10"
    assert lookup["DS6601"]["permits_2026_nr"] == "3"
    assert lookup["DS6601"]["permits_2026_total"] == "13"
    assert lookup["DS6610"]["permits_2026_total"] == "12"
    assert lookup["DS6626"]["permits_2026_res"] == "5"
    assert lookup["DS6626"]["permits_2026_nr"] == "2"
    assert lookup["DS6627"]["permits_2026_total"] == "3"
    assert sum(int(row["permits_2026_total"]) for row in rows) == 85


def test_desert_bighorn_reviewed_export_carries_mapping_law_columns() -> None:
    run_script()
    rows = read_csv(REVIEWED_EXPORT)

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
    assert all(row["boundary_id"] for row in rows)


def test_desert_bighorn_source_matches_database_and_rac_2026_values() -> None:
    run_script()
    db_rows = read_csv(DB_COMPARE)
    rac_rows = read_csv(RAC_COMPARE)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert {row["comparison_status"] for row in db_rows} == {"MATCH"}
    assert {row["comparison_status"] for row in rac_rows} == {"MATCH"}
    assert summary["database_mismatch_count"] == 0
    assert summary["rac_mismatch_count"] == 0
    assert summary["source_total_permits_2026"] == 85


def test_desert_bighorn_conservation_rows_are_parallel_not_replacements() -> None:
    run_script()
    rows = {row["conservation_hunt_code"]: row for row in read_csv(PARALLEL)}

    assert rows["DS1002"]["public_parallel_hunt_codes"] == "DS6601"
    assert rows["DS1003"]["public_parallel_hunt_codes"] == "DS6626|DS6627"
    assert rows["DS1004"]["public_parallel_hunt_codes"] == "DS6608|DS6624"
    assert rows["DS1006"]["public_parallel_hunt_codes"] == "DS6603"
    assert rows["DS1007"]["public_parallel_hunt_codes"] == "DS6610"
    assert rows["DS6605"]["public_parallel_hunt_codes"] == "DS6621"
    assert {row["resolution_status"] for row in rows.values()} == {"RESOLVED_PARALLEL_NOT_REPLACEMENT"}
