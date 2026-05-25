import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "finalize-draw-results-cumulative-database.py"
TRUTH_ROOT = ROOT / "data_truth" / "draw_results_truth" / "normalized"
LONG = TRUTH_ROOT / "draw_results_long.csv"
SOURCE_AUDIT = TRUTH_ROOT / "draw_results_all_years_source_audit.csv"
SUMMARY = TRUTH_ROOT / "draw_results_all_years_summary.json"
SUMMARY_MD = TRUTH_ROOT / "draw_results_all_years_summary.md"


def run_builder():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_draw_results_cumulative_outputs_exist_and_validate():
    run_builder()

    assert LONG.exists()
    assert SOURCE_AUDIT.exists()
    assert SUMMARY.exists()
    assert SUMMARY_MD.exists()
    assert (ROOT / "processed_data" / "draw_results_all_years_source_audit.csv").exists()
    assert (ROOT / "processed_data" / "draw_results_all_years_summary.json").exists()
    assert (ROOT / "processed_data" / "draw_results_all_years_summary.md").exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["blocker_count"] == 0
    assert summary["blank_hunt_code_rows"] == 0
    assert summary["invalid_year_rows"] == 0
    assert summary["duplicate_key_count"] == 0


def test_draw_results_cumulative_counts_are_locked():
    run_builder()
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["normalized_long_rows"] == 176753
    assert summary["unique_draw_years"] == ["2021", "2022", "2023", "2024", "2025", "2026"]
    assert summary["draw_year_counts"] == {
        "2021": 27519,
        "2022": 18688,
        "2023": 17128,
        "2024": 37128,
        "2025": 75194,
        "2026": 1096,
    }
    assert summary["model_target_year_counts"] == {
        "2022": 27519,
        "2023": 18688,
        "2024": 17128,
        "2025": 37128,
        "2026": 75194,
        "2027": 1096,
    }


def test_draw_results_cumulative_key_contract_and_crosswalk_presence():
    run_builder()
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["duplicate_key_fields"] == ["hunt_code", "year", "draw_pool", "residency", "points"]
    assert summary["active_database_hunt_codes"] == 1411
    assert summary["crosswalk_current_code_count"] == 169
    assert summary["crosswalk_current_codes_present_in_draw_rows"] >= 140

    source_rows = read_rows(SOURCE_AUDIT)
    assert source_rows
    assert sum(int(row["row_count"]) for row in source_rows) == summary["normalized_long_rows"]
