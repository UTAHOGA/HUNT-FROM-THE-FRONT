import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-ea-private-lands-canonical-2026.py"
NORMALIZED = (
    ROOT
    / "data_truth"
    / "permit_overlay_truth"
    / "normalized"
    / "elk_antlerless_private_lands_EA_2026_canonical.csv"
)
COMPARISON = (
    ROOT
    / "data_truth"
    / "permit_overlay_truth"
    / "validation"
    / "elk_antlerless_private_lands_EA_2026_vs_DATABASE.csv"
)
SUMMARY = (
    ROOT
    / "data_truth"
    / "permit_overlay_truth"
    / "validation"
    / "elk_antlerless_private_lands_EA_2026_summary.json"
)


def run_validation():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_ea_private_lands_canonical_outputs_are_written():
    run_validation()
    assert NORMALIZED.exists()
    assert COMPARISON.exists()
    assert SUMMARY.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["source_rows"] == 27
    assert summary["unique_hunt_codes"] == 27
    assert summary["source_total_permits_2026"] == 9830
    assert summary["database_missing_count"] == 0
    assert summary["blocker_count"] == 0
    assert summary["source_status"] == "CANONICAL_USER_SUPPLIED_DWR_HUNT_PLANNER_EVIDENCE"


def test_ea_private_lands_canonical_rows_are_clean_and_ea_only():
    run_validation()
    rows = read_csv(NORMALIZED)
    assert len(rows) == 27
    assert all(row["hunt_code"].startswith("EA") for row in rows)
    assert all(row["sex_type"] == "Antlerless" for row in rows)
    assert all(row["species"] == "Elk" for row in rows)
    assert all(row["hunt_type"] == "Private Lands Only" for row in rows)
    assert all(row["permits_2026_total_numeric"].isdigit() for row in rows)
    assert len({row["hunt_code"] for row in rows}) == len(rows)


def test_ea_private_lands_canonical_flags_database_mismatches_without_promotion():
    run_validation()
    rows = read_csv(COMPARISON)
    mismatches = [
        row
        for row in rows
        if row["comparison_status"] == "DATABASE_PROTECTED_VALUE_DIFFERS_FROM_CANONICAL_SOURCE"
    ]
    assert {row["hunt_code"] for row in mismatches} == {
        "EA2012",
        "EA2015",
        "EA2016",
        "EA2027",
        "EA2046",
    }
    assert all("do not overwrite" in row["review_action"] for row in mismatches)
