from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "harvest_results_truth" / "validation"
SUMMARY = VALIDATION / "harvest_2023_moose_gap_fill_summary.json"
CANDIDATES = VALIDATION / "harvest_2023_moose_gap_fill_candidates.csv"
REPORT = ROOT / "processed_data" / "harvest_2023_moose_gap_fill_audit.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_2023_moose_gap_fill_audit_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-harvest-2023-moose-gap-fill-candidates.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert CANDIDATES.exists()
    assert REPORT.exists()


def test_2023_moose_gap_fill_summary_is_locked() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["status"] == "PASS"
    assert summary["gap_rows_reviewed"] == 8
    assert summary["high_confidence_fill_count"] == 1
    assert summary["high_confidence_fill_mappings"] == {"MB6252": "MB6258"}
    assert summary["paired_harvest_target_count"] == 1
    assert summary["paired_harvest_target_codes"] == ["MB6258"]
    assert summary["retained_harvest_only_codes"] == ["MB6200", "MB6209", "MB6216", "MB6217", "MB6220", "MB6254"]
    assert summary["runtime_database_changes_made"] == "NO"


def test_jacobs_creek_crosswalk_pair_is_review_evidence_only() -> None:
    candidate_rows = {row["gap_code"]: row for row in rows(CANDIDATES)}

    mb6252 = candidate_rows["MB6252"]
    assert mb6252["gap_type"] == "DRAW_ONLY"
    assert mb6252["candidate_fill_action"] == "CROSSWALK_TO_HARVEST_CODE"
    assert mb6252["candidate_harvest_code"] == "MB6258"
    assert mb6252["confidence"] == "HIGH"
    assert mb6252["promote_to_runtime"] == "NO"
    assert "Jacob's Creek" in mb6252["reason"]

    mb6258 = candidate_rows["MB6258"]
    assert mb6258["gap_type"] == "HARVEST_ONLY_PAIRED_TARGET"
    assert mb6258["candidate_fill_action"] == "HARVEST_CODE_USED_TO_FILL_DRAW_GAP"
    assert mb6258["candidate_harvest_code"] == "MB6258"
    assert mb6258["confidence"] == "HIGH"
    assert mb6258["promote_to_runtime"] == "NO"


def test_remaining_2023_moose_gaps_are_not_force_filled() -> None:
    candidate_rows = rows(CANDIDATES)
    retained = [row for row in candidate_rows if row["candidate_fill_action"] == "KEEP_HARVEST_ONLY"]

    assert [row["gap_code"] for row in retained] == ["MB6200", "MB6209", "MB6216", "MB6217", "MB6220", "MB6254"]
    assert {row["review_status"] for row in retained} == {"RETAIN_HARVEST_ONLY_NO_DRAW_FILL"}
    assert {row["promote_to_runtime"] for row in retained} == {"NO"}
