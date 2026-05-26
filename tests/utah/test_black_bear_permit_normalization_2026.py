import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/normalize-black-bear-permits-2026.py"
NORMALIZED = ROOT / "data_truth/permit_overlay_truth/normalized/black_bear_permits_2026_canonical.csv"
DB_COMPARE = ROOT / "data_truth/permit_overlay_truth/validation/black_bear_permits_2026_vs_DATABASE.csv"
CODE_COMPARE = ROOT / "data_truth/permit_overlay_truth/validation/black_bear_2026_vs_2025_code_comparison.csv"
SUMMARY = ROOT / "data_truth/permit_overlay_truth/validation/black_bear_permits_2026_summary.json"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"


def run_script() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def by_code(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["hunt_code"]: row for row in rows}


def test_black_bear_source_continuation_rows_are_folded_into_one_row_per_code() -> None:
    run_script()
    rows = read_csv(NORMALIZED)
    lookup = by_code(rows)

    assert len(rows) == 106
    assert len(lookup) == 106
    assert lookup["BR1008"]["permits_2026_res"] == "26"
    assert lookup["BR1008"]["permits_2026_nr"] == "2"
    assert lookup["BR1008"]["permits_2026_total"] == "28"
    assert lookup["BR1017"]["permits_2026_res"] == "0"
    assert lookup["BR1017"]["permits_2026_nr"] == "2"
    assert lookup["BR1017"]["permits_2026_total"] == "2"
    assert lookup["BR7022"]["permits_2026_res"] == "40"
    assert lookup["BR7022"]["permits_2026_nr"] == "3"
    assert lookup["BR7022"]["permits_2026_total"] == "43"
    assert lookup["BR7326"]["permits_2026_res"] == "13"
    assert lookup["BR7326"]["permits_2026_nr"] == "1"
    assert lookup["BR7326"]["permits_2026_total"] == "14"


def test_br7307_keeps_total_only_conservation_lock() -> None:
    run_script()
    lookup = by_code(read_csv(NORMALIZED))
    br7307 = lookup["BR7307"]

    assert br7307["permits_2026_res"] == ""
    assert br7307["permits_2026_nr"] == ""
    assert br7307["permits_2026_total"] == "4"
    assert br7307["permit_count_status"] == "TOTAL_ONLY"
    assert "Conservation" in br7307["notes"]


def test_database_comparison_has_no_black_bear_blockers_after_promotion() -> None:
    run_script()
    comparison = read_csv(DB_COMPARE)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["database_after_promotion"]["numeric_mismatch_count"] == 0
    assert summary["database_after_promotion"]["missing_database_count"] == 0
    assert not [row for row in comparison if row["comparison_status"] in {"NUMERIC_MISMATCH", "MISSING_DATABASE_ROW"}]


def test_database_now_carries_promoted_br_splits_and_source_lineage() -> None:
    run_script()
    lookup = by_code([row for row in read_csv(DATABASE) if row["hunt_code"].startswith("BR")])

    assert lookup["BR1008"]["permits_2026_res"] == "26"
    assert lookup["BR1008"]["permits_2026_nr"] == "2"
    assert lookup["BR1008"]["permits_2026_total"] == "28"
    assert lookup["BR1008"]["permit_allotment_2026_res"] == "26"
    assert lookup["BR1008"]["permit_allotment_2026_nr"] == "2"
    assert lookup["BR1008"]["permit_allotment_2026_total"] == "28"
    assert lookup["BR1008"]["permit_allotment_2026_status"] == "FULL_SPLIT"
    assert lookup["BR1008"]["permits_2026_source"] == "2026 DWR Hunt Planner black bear permits CSV"
    assert lookup["BR7307"]["permits_2026_total"] == "4"
    assert lookup["BR7307"]["permit_allotment_2026_status"] == "TOTAL_ONLY"


def test_2026_to_2025_code_comparison_is_written() -> None:
    run_script()
    rows = read_csv(CODE_COMPARE)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert rows
    assert len({row["hunt_code"] for row in rows}) == len(rows)
    assert "codes_present_2026_missing_2025" in summary["code_comparison"]
    assert "codes_present_2025_missing_2026" in summary["code_comparison"]
