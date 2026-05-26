import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/normalize-buck-deer-permits-2026.py"
NORMALIZED = ROOT / "data_truth/permit_overlay_truth/normalized/buck_deer_permits_2026_canonical.csv"
REVIEWED_LE = (
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 buck deer limited entry reviewed res-nr-total.csv"
)
REVIEWED_PRIVATE = (
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 buck deer private land reviewed res-nr-total.csv"
)
DB_COMPARE = ROOT / "data_truth/permit_overlay_truth/validation/buck_deer_permits_2026_vs_DATABASE.csv"
RAC_COMPARE = ROOT / "data_truth/permit_overlay_truth/validation/buck_deer_limited_entry_2026_vs_RAC.csv"
PRIVATE_COMPLETENESS = (
    ROOT / "data_truth/permit_overlay_truth/validation/buck_deer_private_land_2026_source_completeness.csv"
)
SUMMARY = ROOT / "data_truth/permit_overlay_truth/validation/buck_deer_permits_2026_summary.json"


def run_script() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def by_code(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["hunt_code"]: row for row in rows}


def test_buck_deer_limited_entry_and_private_rows_are_normalized() -> None:
    run_script()
    rows = read_csv(NORMALIZED)
    lookup = by_code(rows)

    assert len(rows) == 76
    assert len(lookup) == 76
    assert lookup["DB1011"]["permits_2026_res"] == "55"
    assert lookup["DB1011"]["permits_2026_nr"] == "6"
    assert lookup["DB1011"]["permits_2026_total"] == "61"
    assert lookup["DB1108"]["permits_2026_total"] == "30"
    assert lookup["LD1001"]["permit_count_status"] == "NO_PUBLISHED_NUMERIC_PERMIT"
    assert lookup["LO0010"]["hunt_name"] == "Diamond Mtn Landowner Association"
    assert lookup["LO0010"]["weapon"] == "Muzzleloader"
    assert sum(int(row["permits_2026_total"] or 0) for row in rows) == 1428


def test_buck_deer_reviewed_exports_carry_mapping_law_columns() -> None:
    run_script()
    for path in [REVIEWED_LE, REVIEWED_PRIVATE]:
        rows = read_csv(path)
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


def test_buck_deer_source_matches_database_and_rac_numeric_values() -> None:
    run_script()
    db_rows = read_csv(DB_COMPARE)
    rac_rows = read_csv(RAC_COMPARE)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert {row["numeric_comparison_status"] for row in db_rows} == {"MATCH"}
    assert not [row for row in rac_rows if row["comparison_status"] == "RAC_DIFFERENCE"]
    assert summary["database_mismatch_count"] == 0
    assert summary["rac_mismatch_count"] == 0
    assert summary["source_total_permits_2026"] == 1428


def test_private_land_deer_source_omission_is_repaired_in_reviewed_export() -> None:
    run_script()
    completeness = {row["hunt_code"]: row for row in read_csv(PRIVATE_COMPLETENESS)}

    assert completeness["LO0010"]["source_presence_status"] == "SOURCE_FILE_OMITS_EXPECTED_CURRENT_CODE"
    assert completeness["LO0010"]["database_presence_status"] == "PRESENT_IN_DATABASE"
    assert completeness["LD1001"]["source_presence_status"] == "PRESENT_IN_SOURCE"
