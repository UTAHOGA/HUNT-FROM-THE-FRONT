from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "processed_data/2026_hunt_code_family_gap_scan_summary.json"
DETAIL = ROOT / "processed_data/2026_hunt_code_family_gap_scan.csv"
REPORT = ROOT / "processed_data/2026_hunt_code_family_gap_scan.md"


def test_hunt_code_family_gap_scan_runs_and_writes_outputs() -> None:
    subprocess.run([sys.executable, "scripts/scan-2026-hunt-code-family-gaps.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert DETAIL.exists()
    assert REPORT.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "CURRENT_2026_HUNT_CODE_FAMILY_GAP_SCAN"
    assert summary["database_code_count"] == 1411
    assert summary["hunt_master_code_count"] == 1471
    assert summary["point_ladder_code_count"] == 1471
    assert summary["draw_reality_code_count"] == 1623
    assert summary["predictive_v2_code_count"] == 1471
    assert summary["family_count"] == 21
    assert summary["resolved_family_count"] == 21
    assert summary["predictive_gap_family_count"] == 0
    assert summary["required_surface_blocker_family_count"] == 0
    assert summary["total_missing_predictive_v2_current_database_codes"] == 0
    assert summary["total_required_surface_missing_current_database_codes"] == 0
    assert set(summary["resolved_families"]) == {
        "BR",
        "BI",
        "CG",
        "DA",
        "DB",
        "DS",
        "EA",
        "EB",
        "EL",
        "EX",
        "GO",
        "LD",
        "LO",
        "LP",
        "MA",
        "MB",
        "PB",
        "PD",
        "RE",
        "RS",
        "TK",
    }


def test_hunt_code_family_gap_scan_ranks_largest_predictive_gaps() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    ranked = summary["predictive_gap_families_ranked"]

    assert ranked == []


def test_hunt_code_family_gap_scan_marks_resolved_reference_families() -> None:
    with DETAIL.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["code_prefix"]: row for row in csv.DictReader(handle)}

    assert rows["BR"]["status"] == "RESOLVED"
    assert rows["BR"]["database_code_count"] == "106"
    assert rows["BR"]["predictive_v2_code_count"] == "106"
    assert rows["BR"]["missing_predictive_v2_count"] == "0"

    assert rows["TK"]["status"] == "RESOLVED"
    assert rows["TK"]["database_code_count"] == "18"
    assert rows["TK"]["predictive_v2_code_count"] == "18"
    assert rows["TK"]["missing_predictive_v2_count"] == "0"

    for prefix in ("BI", "CG", "DA", "DB", "DS", "EA", "EB", "EL", "EX", "LD", "LO", "LP", "PD", "RE", "RS"):
        assert rows[prefix]["status"] == "RESOLVED"
        assert rows[prefix]["missing_predictive_v2_count"] == "0"
