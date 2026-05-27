from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "harvest_results_truth" / "validation"
SUMMARY = VALIDATION / "harvest_year_by_year_hardening_2026_summary.json"
YEAR_CSV = VALIDATION / "harvest_year_by_year_hardening_2026.csv"
MISSING_CSV = VALIDATION / "harvest_year_by_year_hardening_2026_missing_codes.csv"
HISTORICAL_ONLY_CSV = VALIDATION / "harvest_year_by_year_hardening_2026_historical_only_codes.csv"
REPORT_MD = ROOT / "processed_data" / "harvest_year_by_year_hardening_2026.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_harvest_hardening_audit_runs_and_writes_outputs() -> None:
    subprocess.run([sys.executable, "scripts/audit-harvest-year-by-year-hardening-2026.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert YEAR_CSV.exists()
    assert MISSING_CSV.exists()
    assert HISTORICAL_ONLY_CSV.exists()
    assert REPORT_MD.exists()


def test_harvest_hardening_uses_current_1449_code_universe() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["current_database_unique_hunt_codes"] == 1449
    assert summary["unique_reported_hunt_years"] == ["2021", "2022", "2023", "2024", "2025"]
    assert summary["harvest_best_rows"] == 5151
    assert summary["harvest_long_rows"] == 68657
    assert summary["blocker_count"] == 0


def test_harvest_hardening_2025_coverage_is_current_best_year() -> None:
    year_rows = {row["reported_hunt_year"]: row for row in rows(YEAR_CSV)}

    assert year_rows["2025"]["current_database_hunt_codes"] == "1449"
    assert int(year_rows["2025"]["current_database_codes_covered"]) >= 1120
    assert int(year_rows["2025"]["current_database_codes_missing"]) <= 330
    assert year_rows["2025"]["model_target_years"] == "2026"


def test_harvest_hardening_missing_codes_are_review_targets_not_promotions() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    missing_rows = rows(MISSING_CSV)

    assert len(missing_rows) == summary["missing_code_rows"]
    assert {row["covered_in_any_harvest_year"] for row in missing_rows} <= {"YES", "NO"}
    assert all(row["missing_reason"] for row in missing_rows)
    assert all(row["hunt_code"] for row in missing_rows)


def test_historical_only_harvest_codes_are_listed_for_crosswalk_review() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    historical_rows = rows(HISTORICAL_ONLY_CSV)

    assert len(historical_rows) == summary["historical_only_harvest_codes_not_current_database"]
    assert len(historical_rows) >= 150
    assert all(row["review_status"] == "HISTORICAL_CODE_NOT_IN_CURRENT_DATABASE" for row in historical_rows)
