from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "retire-current-hunt-codes-2026.py"
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
LEDGER = ROOT / "data_truth" / "crosswalk_truth" / "normalized" / "retired_current_hunt_codes_2026.csv"
SUMMARY = ROOT / "data_truth" / "crosswalk_truth" / "validation" / "retired_current_hunt_codes_2026_summary.json"

RETIRED_CODES = {
    "EA1007",
    "EA1053",
    "EA1287",
    "EA1288",
    "EA1289",
    "EA1290",
    "EA1291",
    "EA1292",
    "EA1293",
    "EA1294",
    "EA1295",
    "EA1296",
    "EA1297",
    "EA1298",
    "EA1299",
    "EA1300",
    "PD1039",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_retirement_script_is_idempotent_after_retirement() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["newly_retired_row_count"] == 0
    assert summary["total_retired_codes"] == sorted(RETIRED_CODES)
    assert summary["total_retired_ledger_row_count"] == 17


def test_retired_codes_removed_from_current_database_and_preserved_in_ledger() -> None:
    database_rows = read_rows(DATABASE)
    database_codes = {row["hunt_code"] for row in database_rows}
    assert RETIRED_CODES.isdisjoint(database_codes)
    assert len(database_rows) == len(database_codes) == 1394
    assert all(row["boundary_id"] for row in database_rows)

    ledger_rows = read_rows(LEDGER)
    ledger_codes = {row["hunt_code"] for row in ledger_rows}
    assert ledger_codes == RETIRED_CODES
    assert {row["retirement_reason"] for row in ledger_rows} == {
        "USER_CONFIRMED_CEASES_TO_EXIST_ONLINE_EFFECTIVE_2026"
    }
    assert {row["effective_year"] for row in ledger_rows} == {"2026"}

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["total_retired_codes"] == sorted(RETIRED_CODES)
    assert summary["total_retired_ledger_row_count"] == 17
    assert summary["database_row_count_after"] == 1394
    assert summary["remaining_blank_boundary_id_count"] == 0
    assert summary["remaining_duplicate_hunt_code_count"] == 0
    assert summary["blocker_count"] == 0
