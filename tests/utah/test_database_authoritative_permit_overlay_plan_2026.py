import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build-database-authoritative-permit-overlay-plan-2026.py"
OUTPUT = ROOT / "processed_data" / "database_authoritative_permit_overlay_plan_2026.csv"
SUMMARY = ROOT / "processed_data" / "database_authoritative_permit_overlay_plan_2026_summary.json"
VALIDATION = (
    ROOT
    / "data_truth"
    / "comparison_outputs"
    / "validation"
    / "database_authoritative_permit_overlay_plan_2026_summary.json"
)


def run_plan():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_rows():
    with OUTPUT.open(newline="", encoding="utf-8") as handle:
        return {row["hunt_code"]: row for row in csv.DictReader(handle)}


def test_database_authoritative_overlay_plan_outputs_are_written():
    run_plan()
    assert OUTPUT.exists()
    assert SUMMARY.exists()
    assert VALIDATION.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["output_row_count"] == 1412
    assert summary["unique_hunt_codes"] == 1412
    assert summary["target_only_blocker_codes"] == ["DB1276"]
    assert summary["action_counts"]["USE_DATABASE_2026_PERMITS_IN_DERIVED_OUTPUTS"] > 250
    assert "2026 permit/allotment cells" in summary["guardrail"]
    assert "2025 or older permit fields are historical evidence" in summary["guardrail"]
    assert "does not modify DATABASE.csv" in summary["guardrail"]


def test_overlay_plan_uses_database_values_for_target_zero_placeholders():
    run_plan()
    rows = read_rows()

    db1200 = rows["DB1200"]
    assert db1200["target_2026_total"] == "0"
    assert db1200["database_2026_total"] == "3"
    assert db1200["resolved_2026_total"] == "3"
    assert db1200["resolved_2026_source"] == "DATABASE.permits_2026"
    assert db1200["overlay_action"] == "USE_DATABASE_2026_PERMITS_IN_DERIVED_OUTPUTS"
    assert db1200["database_numeric_protected"] == "YES"


def test_overlay_plan_blocks_target_codes_missing_database_and_adds_database_only_codes():
    run_plan()
    rows = read_rows()

    assert rows["DB1276"]["overlay_action"] == "BLOCK_TARGET_CODE_NOT_IN_DATABASE"
    assert rows["DB1276"]["review_priority"] == "HIGH"

    assert rows["DS1000"]["row_origin"] == "DATABASE_ONLY"
    assert rows["DS1000"]["overlay_action"] == "ADD_DATABASE_CODE_TO_DERIVED_UNIVERSE"
