from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT_SUMMARY = ROOT / "processed_data/2024_antlerless_draw_results_audit.json"
PROMOTION_SUMMARY = ROOT / "processed_data/2026_antlerless_predictive_v2_reference_promotion_summary.json"
RECONCILIATION_SUMMARY = ROOT / "processed_data/2026_antlerless_hunt_code_reconciliation_summary.json"
DRAW_ROWS = ROOT / "data_truth/draw_results_truth/extracted/2024_antlerless_draw_results_hunt_rows.csv"
RECONCILIATION = ROOT / "data_truth/draw_results_truth/validation/2026_antlerless_hunt_code_reconciliation.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"

EXPECTED_REFERENCE_PREFIX_COUNTS = {"DA": 2, "EA": 51, "PD": 8, "RE": 1}
EXPECTED_REFERENCE_SAMPLE_CODES = {"DA1048", "EA1007", "EA1267", "PD1039", "RE1000"}


def test_antlerless_hunt_code_resolution_runs_and_writes_outputs() -> None:
    subprocess.run([sys.executable, "scripts/resolve-antlerless-hunt-codes-2026.py"], cwd=ROOT, check=True)

    assert AUDIT_SUMMARY.exists()
    assert PROMOTION_SUMMARY.exists()
    assert RECONCILIATION_SUMMARY.exists()
    assert DRAW_ROWS.exists()
    assert RECONCILIATION.exists()

    audit = json.loads(AUDIT_SUMMARY.read_text(encoding="utf-8"))
    assert audit["classification"] == "ANTLERLESS_DRAW_RESULTS_TRUTH_SOURCE_AUDIT"
    assert audit["source_sha256"] == "21ea12abd24abb29b074520eccae1ab1b689d6e969d622803f220c0ca4664789"
    assert audit["pdf_pages"] == 198
    assert audit["text_lines"] == 5346
    assert audit["draw_result_rows"] == 198
    assert audit["unique_draw_result_hunt_codes"] == 198
    assert audit["draw_result_prefix_counts"] == {"DA": 21, "EA": 158, "MA": 2, "PD": 16, "RE": 1}
    assert audit["blockers"] == 0

    reconciliation = json.loads(RECONCILIATION_SUMMARY.read_text(encoding="utf-8"))
    assert reconciliation["classification"] == "ANTLERLESS_HUNT_CODE_RECONCILIATION"
    assert reconciliation["target_prefixes"] == ["DA", "EA", "PD", "RE"]
    assert reconciliation["current_database_code_count"] == 265
    assert reconciliation["draw_results_2024_code_count"] == 196
    assert reconciliation["current_database_codes_present_in_2024_draw_results_count"] == 182
    assert reconciliation["current_database_reconciliation_failure_count"] == 0
    assert reconciliation["blockers"] == 0


def test_antlerless_reference_codes_promoted_without_modeling_odds() -> None:
    promotion = json.loads(PROMOTION_SUMMARY.read_text(encoding="utf-8"))
    assert promotion["classification"] == "ANTLERLESS_REFERENCE_PROMOTION"
    assert promotion["target_prefixes"] == ["DA", "EA", "PD", "RE"]
    assert promotion["promoted_reference_hunt_code_count"] == 62
    assert promotion["still_missing_predictive_hunt_code_count"] == 0
    assert promotion["duplicate_reference_key_count"] == 0

    promoted_codes = set(promotion["promoted_reference_hunt_codes"])
    assert len(promoted_codes) == 62
    assert EXPECTED_REFERENCE_SAMPLE_CODES.issubset(promoted_codes)

    with PREDICTIVE.open(newline="", encoding="utf-8-sig") as handle:
        reference_rows = [
            row
            for row in csv.DictReader(handle)
            if row["model_version"] == "antlerless_reference_v1.0.0"
            and row["hunt_code"] in promoted_codes
        ]

    assert len({row["hunt_code"] for row in reference_rows}) == 62
    assert {row["algorithm_status"] for row in reference_rows} == {"ANTLERLESS_REFERENCE"}
    assert {row["modeled_by_engine"] for row in reference_rows} == {"False"}
    assert {row["probability_model"] for row in reference_rows} == {"NONE"}
    assert {row["display_odds_text"] for row in reference_rows} == {"Antlerless reference only; odds not modeled"}
    assert {row["data_quality_grade"] for row in reference_rows} == {"A"}

    prefix_counts: dict[str, int] = {}
    for row in reference_rows:
        prefix = "".join(char for char in row["hunt_code"] if char.isalpha())
        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
    assert prefix_counts == EXPECTED_REFERENCE_PREFIX_COUNTS


def test_antlerless_reconciliation_distinguishes_prior_draw_and_current_reference_basis() -> None:
    with RECONCILIATION.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["hunt_code"]: row for row in csv.DictReader(handle)}

    assert rows["EA1010"]["source_basis"] == "prior_2024_antlerless_draw_results"
    assert rows["EA1010"]["current_database_reconciliation_status"] == "PASS"
    assert rows["EA1010"]["present_in_2024_antlerless_draw_results"] == "true"

    assert rows["EA1007"]["source_basis"] == "current_2026_database_reference_only"
    assert rows["EA1007"]["current_database_reconciliation_status"] == "PASS"
    assert rows["EA1007"]["present_in_2024_antlerless_draw_results"] == "false"

    assert rows["PD1039"]["source_basis"] == "current_2026_database_reference_only"
    assert rows["RE1000"]["source_basis"] == "prior_2024_antlerless_draw_results"
