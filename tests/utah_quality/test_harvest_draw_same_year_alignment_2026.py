from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "comparison_outputs" / "validation"
SUMMARY = VALIDATION / "harvest_draw_same_year_alignment_2026_summary.json"
YEAR_CSV = VALIDATION / "harvest_draw_same_year_alignment_2026.csv"
DETAIL_CSV = VALIDATION / "harvest_draw_same_year_alignment_2026_code_detail.csv"
REPORT_MD = ROOT / "processed_data" / "harvest_draw_same_year_alignment_2026.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_same_year_alignment_audit_runs_and_writes_outputs() -> None:
    subprocess.run([sys.executable, "scripts/audit-harvest-draw-same-year-alignment-2026.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert YEAR_CSV.exists()
    assert DETAIL_CSV.exists()
    assert REPORT_MD.exists()


def test_same_year_alignment_uses_2021_to_2021_not_2026_completeness() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    baseline = summary["baseline_2021"]

    assert baseline["year"] == "2021"
    assert baseline["harvest_native_unique_hunt_codes"] == "974"
    assert baseline["draw_native_unique_hunt_codes"] == "550"
    assert baseline["comparison_use"] == "SAME_YEAR_NATIVE_ALIGNMENT_NOT_2026_COMPLETENESS"
    assert "No historical year is judged against the 2026 active hunt-code universe" in " ".join(summary["guardrails"])


def test_same_year_alignment_detail_rows_are_review_evidence() -> None:
    detail_rows = rows(DETAIL_CSV)
    statuses = {row["alignment_status"] for row in detail_rows}

    assert "HARVEST_ONLY_SAME_YEAR" in statuses
    assert "DRAW_ONLY_SAME_YEAR" in statuses
    assert all(row["year"] for row in detail_rows)
    assert all(row["hunt_code"] for row in detail_rows)
