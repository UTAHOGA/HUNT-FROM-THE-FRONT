from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
REFERENCE = ROOT / "processed_data" / "hunt_unit_reference_linked.csv"
SUMMARY = ROOT / "data_truth" / "comparison_outputs" / "validation" / "hunt_research_reference_linked_2026_summary.json"

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


def test_research_reference_repair_is_idempotent_and_current() -> None:
    subprocess.run([sys.executable, "scripts/repair-hunt-research-reference-linked-2026.py"], cwd=ROOT, check=True)

    database_codes = {row["hunt_code"] for row in read_rows(DATABASE)}
    reference_rows = read_rows(REFERENCE)
    reference_codes = {row["hunt_code"] for row in reference_rows}

    assert reference_codes == database_codes
    assert len(reference_codes) == 1449
    assert sorted(code for code in reference_codes if code.startswith("CG")) == ["CG9999"]
    assert RETIRED_CODES.isdisjoint(reference_codes)

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["artifact"] == "hunt_research_reference_linked_2026"
    assert summary["database_unique_hunt_code_count"] == 1449
    assert summary["reference_unique_hunt_code_count_after"] == 1449
    assert summary["harvest_populated_unique_hunt_code_count"] >= 1110
    assert summary["blocker_count"] == 0
