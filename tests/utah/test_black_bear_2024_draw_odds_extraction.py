import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/extract-black-bear-2024-draw-odds-permits.py"
NORMALIZED = ROOT / "data_truth/draw_results_truth/normalized/black_bear_2024_draw_odds_model_target_2025_permit_totals.csv"
VALIDATION = ROOT / "data_truth/draw_results_truth/validation/black_bear_2024_draw_odds_model_target_2025_vs_DATABASE.csv"
SUMMARY = ROOT / "data_truth/draw_results_truth/validation/black_bear_2024_draw_odds_model_target_2025_summary.json"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def run_script() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_black_bear_2024_draw_odds_extracts_all_hunt_code_totals() -> None:
    run_script()
    rows = read_rows(NORMALIZED)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert len(rows) == 96
    assert len({row["hunt_code"] for row in rows}) == 96
    assert summary["reported_draw_year"] == 2024
    assert summary["model_target_year"] == 2025
    assert summary["source_total_public_permits"] == 943
    assert summary["source_classification_counts"] == {
        "BEAR_PURSUIT_BONUS_DRAW": 9,
        "TRUE_BEAR_BONUS_DRAW": 87,
    }


def test_black_bear_2024_draw_odds_known_rows_parse_resident_and_nonresident_splits() -> None:
    run_script()
    rows = {row["hunt_code"]: row for row in read_rows(NORMALIZED)}

    assert rows["BR1008"]["resident_bonus_permits"] == "13"
    assert rows["BR1008"]["resident_regular_permits"] == "13"
    assert rows["BR1008"]["resident_total_permits"] == "26"
    assert rows["BR1008"]["nonresident_total_permits"] == "2"
    assert rows["BR1008"]["total_public_permits"] == "28"

    assert rows["BR7116"]["resident_bonus_permits"] == "13"
    assert rows["BR7116"]["resident_regular_permits"] == "12"
    assert rows["BR7116"]["resident_total_permits"] == "25"
    assert rows["BR7116"]["nonresident_total_permits"] == "2"
    assert rows["BR7116"]["total_public_permits"] == "27"

    assert rows["BR7316"]["resident_total_permits"] == "13"
    assert rows["BR7316"]["nonresident_total_permits"] == "1"
    assert rows["BR7316"]["total_public_permits"] == "14"


def test_black_bear_2024_draw_odds_validation_preserves_database_review_status() -> None:
    run_script()
    validation = read_rows(VALIDATION)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["database_missing_codes"] == 4
    assert summary["database_match_count"] == 37
    assert summary["database_difference_count"] == 55
    assert {row["hunt_code"] for row in validation if row["database_comparison_status"] == "MISSING_DATABASE_ROW"} == {
        "BR7008",
        "BR7019",
        "BR7108",
        "BR7208",
    }
