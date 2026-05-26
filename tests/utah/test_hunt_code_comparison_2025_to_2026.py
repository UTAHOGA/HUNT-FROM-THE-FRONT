import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "compare-2025-2026-hunt-codes.py"
OUTPUT = ROOT / "processed_data" / "hunt_code_comparison_2025_to_2026.csv"
SUMMARY = ROOT / "processed_data" / "hunt_code_comparison_2025_to_2026_summary.json"
VALIDATION = (
    ROOT
    / "data_truth"
    / "comparison_outputs"
    / "validation"
    / "hunt_code_comparison_2025_to_2026_summary.json"
)


def run_comparison():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_rows():
    with OUTPUT.open(newline="", encoding="utf-8") as handle:
        return {row["hunt_code"]: row for row in csv.DictReader(handle)}


def test_hunt_code_comparison_2025_to_2026_outputs_are_written():
    run_comparison()
    assert OUTPUT.exists()
    assert SUMMARY.exists()
    assert VALIDATION.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["database_2026_universe_count"] == 1411
    assert summary["historical_2025_permit_code_count"] == 1028
    assert summary["current_2026_populated_permit_code_count"] == 1261
    assert summary["exact_same_code_2025_and_2026_count"] == 1027
    assert summary["historical_2025_codes_absent_from_2026_database_count"] == 0
    assert summary["historical_2025_codes_without_2026_permit_count"] == 1
    assert summary["current_2026_populated_codes_without_exact_2025_count"] == 234
    assert summary["current_2026_populated_codes_with_mapped_2025_history_count"] == 133
    assert summary["current_2026_populated_codes_no_2025_history_count"] == 101
    assert summary["current_2026_reference_only_no_2025_or_2026_count"] == 149
    assert "current-to-historical crosswalk" in summary["guardrail"]
    assert "candidate/name-match fields remain review evidence" in summary["guardrail"]


def test_hunt_code_comparison_classifies_exact_and_retired_examples():
    run_comparison()
    rows = read_rows()

    bi6500 = rows["BI6500"]
    assert bi6500["comparison_status"] == "EXACT_SAME_CODE_2025_AND_2026_PERMITTED"
    assert bi6500["has_2025_historical_permits"] == "YES"
    assert bi6500["has_2026_current_permits"] == "YES"
    assert bi6500["permit_delta_basis"] == "EXACT_CODE"

    br7307 = rows["BR7307"]
    assert br7307["comparison_status"] == "HISTORICAL_2025_CODE_PRESENT_BUT_NO_2026_PERMIT_VALUE"
    assert br7307["has_2025_historical_permits"] == "YES"
    assert br7307["has_2026_current_permits"] == "NO"
    assert br7307["review_priority"] == "HIGH"


def test_hunt_code_comparison_identifies_code_changed_and_true_new_examples():
    run_comparison()
    rows = read_rows()

    el3000 = rows["EL3000"]
    assert el3000["comparison_status"] == "CURRENT_2026_CODE_WITH_MAPPED_2025_HISTORY"
    assert el3000["mapped_2025_historical_codes"] == "EB3000"
    assert el3000["crosswalk_status"] == "PROMOTED_PREFIX_SWAP_CANDIDATE"
    assert el3000["permit_delta_basis"] == "CROSSWALK_CANDIDATE_SUM"

    bi6539 = rows["BI6539"]
    assert bi6539["comparison_status"] == "CURRENT_2026_PERMIT_CODE_NO_2025_HISTORY"
    assert bi6539["has_2025_historical_permits"] == "NO"
    assert bi6539["has_2026_current_permits"] == "YES"


def test_hunt_code_comparison_keeps_reference_only_rows_separate():
    run_comparison()
    rows = read_rows()

    cg9999 = rows["CG9999"]
    assert cg9999["comparison_status"] == "CURRENT_2026_REFERENCE_ONLY_NO_2025_OR_2026_PERMITS"
    assert cg9999["has_2025_historical_permits"] == "NO"
    assert cg9999["has_2026_current_permits"] == "NO"
