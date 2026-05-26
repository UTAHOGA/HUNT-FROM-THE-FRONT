import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/resolve-current-reference-codes-2026.py"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
REVIEW_OUTPUT = ROOT / "data_truth/crosswalk_truth/validation/current_reference_codes_2026_review.csv"
SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/current_reference_codes_2026_summary.json"


def run_script():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_current_reference_review_outputs_and_cougar_unlimited_lock():
    run_script()

    assert REVIEW_OUTPUT.exists()
    assert SUMMARY.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["blocker_count"] == 0
    assert summary["reviewed_count"] == 4
    assert summary["unlimited_permit_count"] == 1

    review_rows = {row["hunt_code"]: row for row in read_rows(REVIEW_OUTPUT)}
    assert set(review_rows) == {"CG9999", "EX1000", "LO0008", "LO0011"}
    assert all(row["hunt_code_mapping_status"] == "REVIEWED_CURRENT_REFERENCE" for row in review_rows.values())
    assert all(row["boundary_id_mapping_status"] == "REVIEWED_CURRENT_REFERENCE" for row in review_rows.values())

    database_rows = {row["hunt_code"]: row for row in read_rows(DATABASE)}
    cougar = database_rows["CG9999"]
    assert cougar["season"] == "open"
    assert cougar["permits_2026_total"] == "unlimited"
    assert cougar["permits_2026_res"] == ""
    assert cougar["permits_2026_nr"] == ""
    assert cougar["permit_allotment_2026_total"] == "unlimited"
    assert cougar["permit_allotment_2026_status"] == "UNLIMITED_PERMITS"
    assert cougar["permit_allotment_2026_source_file"] == (
        "pipeline/RAW/hunt_unit_database/2026/csv/2026_cougar.csv"
    )


def test_private_land_and_extended_archery_reference_rows_do_not_get_fake_numbers():
    run_script()
    database_rows = {row["hunt_code"]: row for row in read_rows(DATABASE)}

    for code in ["EX1000", "LO0008", "LO0011"]:
        row = database_rows[code]
        assert row["permits_2026_res"] == ""
        assert row["permits_2026_nr"] == ""
        assert row["permits_2026_total"] == ""
        assert row["permit_allotment_2026_res"] == ""
        assert row["permit_allotment_2026_nr"] == ""
        assert row["permit_allotment_2026_total"] == ""
        assert row["permit_allotment_2026_status"] == "NO_QUOTA_PUBLISHED"
