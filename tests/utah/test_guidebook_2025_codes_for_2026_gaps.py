import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "find-2025-regulation-codes-for-2026-gaps.py"
OUTPUT = ROOT / "processed_data" / "guidebook_2025_codes_for_2026_gaps.csv"
GUIDEBOOK_CODES = ROOT / "processed_data" / "guidebook_2025_extracted_hunt_codes.csv"
SUMMARY = ROOT / "processed_data" / "guidebook_2025_codes_for_2026_gaps_summary.json"
VALIDATION = (
    ROOT
    / "data_truth"
    / "comparison_outputs"
    / "validation"
    / "guidebook_2025_codes_for_2026_gaps_summary.json"
)


def run_lookup():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_rows():
    with OUTPUT.open(newline="", encoding="utf-8-sig") as handle:
        return {row["current_hunt_code"]: row for row in csv.DictReader(handle)}


def test_guidebook_2025_code_lookup_outputs_are_written():
    run_lookup()
    assert OUTPUT.exists()
    assert GUIDEBOOK_CODES.exists()
    assert SUMMARY.exists()
    assert VALIDATION.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["guidebook_unique_codes"] > 700
    assert summary["gap_rows_checked"] == 102
    assert "name-only candidates remain review evidence" in summary["guardrail"]
    assert summary["guidebook_match_status_counts"]["EXACT_CURRENT_CODE_IN_2025_GUIDEBOOK"] >= 2
    assert summary["guidebook_match_status_counts"]["PREFIX_SWAP_CODE_IN_2025_GUIDEBOOK"] >= 3


def test_guidebook_2025_code_lookup_finds_exact_and_prefix_examples():
    run_lookup()
    rows = read_rows()

    eb3168 = rows["EB3168"]
    assert eb3168["guidebook_match_status"] == "EXACT_CURRENT_CODE_IN_2025_GUIDEBOOK"
    assert eb3168["guidebook_candidate_codes"] == "EB3168"
    assert "Cache, Meadowville" in eb3168["guidebook_candidate_lines"]

    el3168 = rows["EL3168"]
    assert el3168["guidebook_match_status"] == "PREFIX_SWAP_CODE_IN_2025_GUIDEBOOK"
    assert el3168["guidebook_candidate_codes"] == "EB3168"
    assert el3168["match_method"] == "EL_to_EB_same_number"

    lo1627 = rows["LO1627"]
    assert lo1627["guidebook_match_status"] == "PREFIX_SWAP_CODE_IN_2025_GUIDEBOOK"
    assert lo1627["guidebook_candidate_codes"] == "DB1627"


def test_guidebook_2025_code_lookup_keeps_name_candidates_and_missing_codes_as_review():
    run_lookup()
    rows = read_rows()

    bi6539 = rows["BI6539"]
    assert bi6539["guidebook_match_status"] == "NAME_SPECIES_CANDIDATES_IN_2025_GUIDEBOOK"
    assert "BI6505" in bi6539["guidebook_candidate_codes"]
    assert bi6539["review_priority"] == "MEDIUM"

    ds1000 = rows["DS1000"]
    assert ds1000["guidebook_match_status"] == "GUIDEBOOK_NO_CODE_FOUND"
    assert ds1000["guidebook_candidate_codes"] == ""

    br7307 = rows["BR7307"]
    assert br7307["comparison_status"] == "HISTORICAL_2025_CODE_PRESENT_BUT_NO_2026_PERMIT_VALUE"


def test_guidebook_2025_code_lookup_outputs_ascii_clean_candidate_text():
    run_lookup()
    bad_tokens = ["\u00e2", "\u00c2", "\ufffd", "\u2013", "\u2014", "\u2020", "\u2021", "\u2022"]
    for path in (OUTPUT, GUIDEBOOK_CODES):
        text = path.read_text(encoding="utf-8-sig")
        assert not any(token in text for token in bad_tokens)

    rows = read_rows()
    assert "Cache (new) DB1627 Oct. 18-Oct. 26" in rows["LO1627"]["guidebook_candidate_lines"]
    assert "Cache (new)" in rows["LO1627"]["guidebook_candidate_names"]
