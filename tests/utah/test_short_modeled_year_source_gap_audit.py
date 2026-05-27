from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "data_truth" / "comparison_outputs" / "validation"
SUMMARY = VALIDATION / "short_modeled_year_source_gap_audit_summary.json"
AUDIT_CSV = VALIDATION / "short_modeled_year_source_gap_audit.csv"
REPORT = ROOT / "processed_data" / "short_modeled_year_source_gap_audit.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_short_modeled_year_source_gap_audit_runs() -> None:
    subprocess.run([sys.executable, "scripts/audit-short-modeled-year-source-gaps.py"], cwd=ROOT, check=True)

    assert SUMMARY.exists()
    assert AUDIT_CSV.exists()
    assert REPORT.exists()


def test_short_modeled_year_summary_locks_ready_sources() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["status"] == "PASS"
    assert summary["modeled_years"] == ["2021", "2024"]
    assert summary["source_evidence_rows"] == 26
    assert summary["local_extraction_ready_rows"] == 20
    assert summary["local_harvest_renormalization_rows"] == 3
    assert summary["runtime_database_changes_made"] == "NO"


def test_2021_obvious_gap_rows_are_present() -> None:
    audit_rows = rows(AUDIT_CSV)
    by_key = {(row["modeled_year"], row["domain"], row["source_family"]): row for row in audit_rows}

    assert by_key[("2021", "draw", "big_game_limited_entry_oil")]["fill_status"] == "NORMALIZED_PRESENT_WITH_SOURCE_LABEL_REVIEW"
    assert by_key[("2021", "draw", "general_season_deer_preference")]["fill_status"] == "LOCAL_SOURCE_READY_FOR_EXTRACTION"
    assert by_key[("2021", "draw", "black_bear")]["fill_status"] == "LOCAL_SOURCE_READY_FOR_EXTRACTION"
    assert by_key[("2021", "draw", "turkey_bonus")]["fill_status"] == "LOCAL_SOURCE_READY_FOR_EXTRACTION"
    assert by_key[("2021", "harvest", "value_bearing_harvest_metrics")]["fill_status"] == "LOCAL_VALUE_BEARING_HARVEST_READY_FOR_RENORMALIZATION"


def test_2024_obvious_gap_rows_are_present() -> None:
    audit_rows = rows(AUDIT_CSV)
    by_key = {(row["modeled_year"], row["domain"], row["source_family"]): row for row in audit_rows}

    assert by_key[("2024", "draw", "general_deer_youth_lifetime_dedicated_bundle")]["fill_status"] == "LOCAL_SOURCE_READY_FOR_EXTRACTION"
    assert by_key[("2024", "draw", "turkey_bonus_and_youth")]["fill_status"] == "LOCAL_SOURCE_READY_FOR_EXTRACTION"
    assert by_key[("2024", "draw", "points_purchase_reference")]["fill_status"] == "REFERENCE_ONLY_NOT_DRAW_ROWS"
    assert by_key[("2024", "harvest", "elk_average_age_supplement")]["fill_status"] == "LOCAL_SUPPLEMENT_READY_FOR_FEATURE_ENRICHMENT"
    assert by_key[("2024", "harvest", "black_bear_harvest_objective_supplement")]["fill_status"] == "LOCAL_SUPPLEMENT_READY_FOR_FEATURE_ENRICHMENT"


def test_short_modeled_year_alignment_counts_are_recorded() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["alignment"]["2021"]["status_counts"] == {"DRAW_ONLY_SAME_YEAR": 23, "HARVEST_ONLY_SAME_YEAR": 447}
    assert summary["alignment"]["2024"]["status_counts"] == {"DRAW_ONLY_SAME_YEAR": 3, "HARVEST_ONLY_SAME_YEAR": 471}
