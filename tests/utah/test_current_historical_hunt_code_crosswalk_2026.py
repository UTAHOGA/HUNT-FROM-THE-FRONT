import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/build-current-historical-hunt-code-crosswalk-2026.py"
OUTPUT = ROOT / "data_truth/crosswalk_truth/normalized/current_to_historical_hunt_code_crosswalk_2026.csv"
SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/current_to_historical_hunt_code_crosswalk_2026_summary.json"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"


def run_builder():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_crosswalk_builder_outputs_validate_against_database():
    run_builder()

    assert OUTPUT.exists()
    assert SUMMARY.exists()

    rows = read_rows(OUTPUT)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["blocker_count"] == 0
    assert summary["database_crosscheck_missing_count"] == 0
    assert summary["duplicate_current_code_count"] == 0
    assert len(rows) == summary["output_row_count"]
    assert len(rows) == summary["target_current_code_count"]

    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        database_codes = {row["hunt_code"] for row in csv.DictReader(handle)}

    assert all(row["current_hunt_code"] in database_codes for row in rows)
    assert all(row["in_database_2026"] == "YES" for row in rows)


def test_private_land_prefix_crosswalks_are_promoted_candidates():
    run_builder()
    rows = {row["current_hunt_code"]: row for row in read_rows(OUTPUT)}

    assert rows["LD1001"]["historical_hunt_code"] == "DB1001"
    assert rows["LD1001"]["relationship_type"] == "PREFIX_SWAP_LD_TO_DB"
    assert rows["LD1001"]["crosswalk_status"] == "PROMOTED_PREFIX_SWAP_CANDIDATE"

    assert rows["LP5025"]["historical_hunt_code"] == "PB5025"
    assert rows["LP5025"]["relationship_type"] == "PREFIX_SWAP_LP_TO_PB"
    assert rows["LP5025"]["crosswalk_status"] == "PROMOTED_PREFIX_SWAP_CANDIDATE"

    assert rows["EL3000"]["historical_hunt_code"] == "EB3000"
    assert rows["EL3000"]["relationship_type"] == "PREFIX_SWAP_EL_TO_EB"
    assert rows["EL3000"]["crosswalk_status"] == "PROMOTED_PREFIX_SWAP_CANDIDATE"


def test_conservation_and_reference_codes_keep_current_truth_with_history_evidence():
    run_builder()
    rows = {row["current_hunt_code"]: row for row in read_rows(OUTPUT)}

    assert rows["RS1001"]["historical_hunt_code"] == "RS6701"
    assert "RS6701" in rows["RS1001"]["candidate_historical_codes"]
    assert rows["RS1001"]["crosswalk_status"] == "PROMOTED_PINNED_CANDIDATE"

    assert rows["DS1004"]["historical_hunt_code"] == "DS6608|DS6624"
    assert rows["DS1004"]["relationship_type"] == "PARALLEL_CONSERVATION_TO_PUBLIC_OIAL_2026"
    assert rows["DS1004"]["crosswalk_status"] == "PROMOTED_PARALLEL_PUBLIC_UNIT_REFERENCE"
    assert rows["DS1004"]["mapping_confidence"] == "HIGH"

    assert rows["DS1003"]["historical_hunt_code"] == "DS6626|DS6627"
    assert rows["DS1003"]["crosswalk_status"] == "PROMOTED_PARALLEL_PUBLIC_UNIT_REFERENCE"
    assert rows["DS6605"]["historical_hunt_code"] == "DS6621"
    assert rows["DS6605"]["crosswalk_status"] == "PROMOTED_PARALLEL_PUBLIC_UNIT_REFERENCE"

    assert rows["BI6527"]["historical_hunt_code"] == "BI6527"
    assert rows["BI6527"]["relationship_type"] == "EXACT_CODE_HISTORY"

    assert rows["EX1000"]["historical_hunt_code"] == ""
    assert rows["EX1000"]["crosswalk_status"] == "CURRENT_REFERENCE_ONLY_NEEDS_REVIEW"

    assert rows["CG9999"]["historical_hunt_code"] == ""
    assert rows["CG9999"]["crosswalk_status"] == "CURRENT_REFERENCE_ONLY_NEEDS_REVIEW"
