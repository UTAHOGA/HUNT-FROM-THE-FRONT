from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "draw_results_truth" / "validation"
SUMMARY = VALIDATION / "draw_year_by_year_hardening_2026_summary.json"
YEAR_CSV = VALIDATION / "draw_year_by_year_hardening_2026.csv"
MISSING_CSV = VALIDATION / "draw_year_by_year_hardening_2026_missing_codes.csv"
REPORT_MD = ROOT / "processed_data" / "draw_year_by_year_hardening_2026.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_draw_hardening_audit_runs_and_writes_outputs() -> None:
    subprocess.run([sys.executable, "scripts/audit-draw-year-by-year-hardening-2026.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert YEAR_CSV.exists()
    assert MISSING_CSV.exists()
    assert REPORT_MD.exists()


def test_draw_hardening_uses_native_year_counts_not_2026_completeness() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    year_rows = {row["draw_year"]: row for row in rows(YEAR_CSV)}

    assert summary["current_database_unique_hunt_codes"] == 1449
    assert "not judge historical draw years against the 2026 active hunt-code count" in " ".join(summary["guardrails"])
    assert "native_unique_draw_hunt_codes" in year_rows["2021"]
    assert year_rows["2021"]["current_database_comparison_use"] == "CROSS_REFERENCE_ONLY_NOT_YEAR_COMPLETENESS"
    assert int(year_rows["2021"]["native_unique_draw_hunt_codes"]) > 0


def test_draw_hardening_captures_fields_for_later_prediction_features() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    field_rows = {row["field"]: row for row in summary["field_capture_status"]}

    assert field_rows["eligible_applicants"]["captured_in_draw_truth"] is True
    assert field_rows["total_drawn"]["captured_in_draw_truth"] is True
    assert field_rows["points"]["captured_in_draw_truth"] is True
    assert field_rows["residency"]["nonblank_rows"] > 0
