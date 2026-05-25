import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit-hunt-master-canonical-permit-consistency.py"
OUTPUT = ROOT / "processed_data" / "hunt_master_canonical_2026_built_permit_deep_dive.csv"
SUMMARY = ROOT / "processed_data" / "hunt_master_canonical_2026_built_permit_deep_dive_summary.json"
VALIDATION = (
    ROOT
    / "data_truth"
    / "comparison_outputs"
    / "validation"
    / "hunt_master_canonical_2026_built_permit_deep_dive_summary.json"
)


def run_audit():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_rows():
    with OUTPUT.open(newline="", encoding="utf-8") as handle:
        return {row["hunt_code"]: row for row in csv.DictReader(handle)}


def test_hunt_master_canonical_permit_deep_dive_outputs_are_written():
    run_audit()
    assert OUTPUT.exists()
    assert SUMMARY.exists()
    assert VALIDATION.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["target_row_count"] == 1289
    assert summary["target_unique_hunt_codes"] == 1289
    assert summary["database_row_count"] == 1411
    assert summary["direct_rac_hunt_code_count"] > 500
    assert summary["target_duplicate_hunt_codes"] == []
    assert "does not promote 2025 permit values" in summary["guardrail"]
    assert "2026 permit/allotment cells" in summary["guardrail"]
    assert "canonical historical source truth" in summary["guardrail"]
    assert "must not be overwritten" in summary["guardrail"]


def test_deep_dive_detects_target_second_triple_as_2026_allotment_for_bison_examples():
    run_audit()
    rows = read_rows()

    bi6505 = rows["BI6505"]
    assert bi6505["target_2026_total"] == "11"
    assert bi6505["database_2026_total"] == "11"
    assert bi6505["database_allotment_2026_total"] == "11"
    assert bi6505["target_2026_vs_database_2026_status"] == "MATCH"
    assert bi6505["target_2026_vs_database_allotment_status"] == "MATCH"
    assert bi6505["target_2025_vs_database_2025_status"] == "MISMATCH"

    bi6506 = rows["BI6506"]
    assert bi6506["target_2026_vs_database_2026_status"] == "MATCH"
    assert bi6506["target_2026_vs_database_allotment_status"] == "MATCH"


def test_deep_dive_flags_zero_placeholder_allotment_cases_for_review():
    run_audit()
    rows = read_rows()

    db1200 = rows["DB1200"]
    assert db1200["target_2025_vs_database_2025_status"] == "MATCH"
    assert db1200["target_2026_total"] == "0"
    assert db1200["database_2026_total"] == "3"
    assert db1200["target_2026_vs_database_2026_status"] == "MISMATCH"
    assert db1200["evidence_confidence"] == "LOW_2025_MATCH_ONLY"
