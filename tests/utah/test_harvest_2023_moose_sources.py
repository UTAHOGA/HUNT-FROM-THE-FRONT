from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "harvest_results_truth" / "validation"
SUMMARY = VALIDATION / "harvest_2023_moose_source_summary.json"
SOURCE_AUDIT = VALIDATION / "harvest_2023_moose_source_files.csv"
CODE_AUDIT = VALIDATION / "harvest_2023_moose_code_reconciliation.csv"
REPORT = ROOT / "processed_data" / "harvest_2023_moose_source_audit.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_2023_moose_harvest_source_audit_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-harvest-2023-moose-sources.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert SOURCE_AUDIT.exists()
    assert CODE_AUDIT.exists()
    assert REPORT.exists()


def test_2023_moose_harvest_source_files_are_byte_anchored() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["status"] == "PASS"
    assert summary["source_file_count"] == 3
    assert summary["byte_match_count"] == 3
    assert summary["review_source_count"] == 0


def test_2023_moose_harvest_counts_are_locked() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    source_rows = {row["source_file"]: row for row in rows(SOURCE_AUDIT)}

    assert summary["bull_moose_harvest_codes"] == 36
    assert summary["antlerless_moose_harvest_codes"] == 3
    assert source_rows["harvest_results_2023_MOOSE_all_sources.csv"]["row_count"] == "36"
    assert source_rows["harvest_results_2023_MOOSE_all_sources.csv"]["permits_sum"] == "171.0"
    assert source_rows["harvest_results_2023_MOOSE_all_sources.csv"]["hunters_afield_sum"] == "170.0"
    assert source_rows["harvest_results_2023_MOOSE_all_sources.csv"]["harvest_sum"] == "162.0"
    assert source_rows["harvest_results_2023_ANTLERLESS_MOOSE_all_sources.csv"]["row_count"] == "3"
    assert source_rows["harvest_results_2023_ANTLERLESS_MOOSE_all_sources.csv"]["permits_sum"] == "9.0"
    assert source_rows["harvest_results_2023_ANTLERLESS_MOOSE_all_sources.csv"]["harvest_sum"] == "8.0"


def test_2023_moose_draw_harvest_reconciliation_gaps_are_explicit() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    code_rows = rows(CODE_AUDIT)

    assert summary["bull_moose_draw_only_codes"] == ["MB6252"]
    assert summary["bull_moose_harvest_only_codes"] == [
        "MB6200",
        "MB6209",
        "MB6216",
        "MB6217",
        "MB6220",
        "MB6254",
        "MB6258",
    ]
    assert summary["antlerless_moose_mismatch_count"] == 0

    mb6252 = [row for row in code_rows if row["hunt_code"] == "MB6252"][0]
    assert mb6252["reconciliation_status"] == "DRAW_ONLY"
    assert mb6252["in_2023_harvest_csv"] == "NO"
    assert mb6252["comparison_bucket"] == "draw_only"


def test_2023_antlerless_moose_all_draw_codes_have_harvest_rows() -> None:
    code_rows = rows(CODE_AUDIT)
    antlerless = [row for row in code_rows if row["moose_family"] == "antlerless_moose"]

    assert {row["hunt_code"] for row in antlerless} == {"MA1000", "MA1005", "MA1006"}
    assert {row["reconciliation_status"] for row in antlerless} == {"DRAW_AND_HARVEST"}
