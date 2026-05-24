from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "processed_data/2023_big_game_application_guidebook_source_audit.json"
TEXT_LINES = ROOT / "data_truth/regulations_truth/normalized/2023_big_game_application_guidebook_text_lines.csv"
NUMBER_TOKENS = ROOT / "data_truth/regulations_truth/normalized/2023_big_game_application_guidebook_number_tokens.csv"
EXPECTED_TEXT_CHECKS = (
    ROOT / "data_truth/regulations_truth/normalized/2023_big_game_application_guidebook_expected_text_checks.csv"
)
HUNT_TABLES = ROOT / "data_truth/regulations_truth/normalized/2023_big_game_application_guidebook_hunt_tables.csv"


def _run_audit() -> None:
    subprocess.run([sys.executable, "scripts/audit-big-game-application-guidebook-2023.py"], cwd=ROOT, check=True)


def test_2023_application_guidebook_source_audit_passes() -> None:
    _run_audit()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["source_file"] == "pipeline/RAW/hunt_unit_database/2023/pdf/regulation/2023_biggameapp.pdf"
    assert summary["expected_title"] == "2023 Utah Big Game Application Guidebook"
    assert summary["expected_source_year"] == "2023"
    assert summary["actual_sha256"] == "7357df71939b084d5e6807a1bc01670bb6f1c04369e550946b1363c57ed2082b"
    assert summary["classification"] == "APPLICATION_GUIDEBOOK_REFERENCE_ONLY"
    assert summary["modeling_guardrail"] == "DO_NOT_USE_AS_DRAW_ODDS_HARVEST_FEATURE_OR_2026_QUOTA_INPUT"
    assert summary["database_reconciliation_effect"] == "NO_DRAW_OR_PREDICTION_ROWS_PROMOTED"
    assert summary["pdf_page_count"] == 80
    assert summary["text_line_count"] == 3915
    assert summary["number_token_count"] == 3422
    assert summary["token_type_counts"] == {"number_or_money": 2841, "date": 508, "code_citation": 73}
    assert summary["hunt_table_row_count"] == 719
    assert summary["hunt_table_unique_code_count"] == 719
    assert summary["hunt_code_prefix_counts"] == {
        "BI": 17,
        "DB": 326,
        "DS": 16,
        "EB": 212,
        "GO": 17,
        "MB": 30,
        "PB": 87,
        "RS": 14,
    }
    assert summary["expected_text_check_count"] == 66
    assert summary["expected_text_check_failures"] == 0
    assert summary["audit_blocker_count"] == 0
    assert all(summary["checks"].values())


def test_2023_application_guidebook_outputs_are_materialized() -> None:
    _run_audit()

    with TEXT_LINES.open(newline="", encoding="utf-8-sig") as handle:
        line_rows = list(csv.DictReader(handle))
    with NUMBER_TOKENS.open(newline="", encoding="utf-8-sig") as handle:
        token_rows = list(csv.DictReader(handle))
    with EXPECTED_TEXT_CHECKS.open(newline="", encoding="utf-8-sig") as handle:
        check_rows = list(csv.DictReader(handle))
    with HUNT_TABLES.open(newline="", encoding="utf-8-sig") as handle:
        hunt_rows = list(csv.DictReader(handle))

    assert len(line_rows) == 3915
    assert len(token_rows) == 3422
    assert len(check_rows) == 66
    assert len(hunt_rows) == 719
    assert {row["status"] for row in check_rows} == {"PASS"}
    assert len({row["hunt_code"] for row in hunt_rows}) == 719

    hunt_by_code = {row["hunt_code"]: row for row in hunt_rows}
    assert hunt_by_code["DB1500"]["guidebook_hunt_name"] == "Beaver"
    assert hunt_by_code["DB1500"]["guidebook_season_text"] == "Aug. 19-Sept. 15"
    assert hunt_by_code["EB3158"]["guidebook_hunt_name"] == "Beaver, East"
    assert hunt_by_code["EB3158"]["guidebook_season_text"] == "Dec. 2-Dec. 17"
    assert hunt_by_code["PB5000"]["species_inferred"] == "Pronghorn"
    assert hunt_by_code["BI6500"]["guidebook_hunt_name"] == "Antelope Island"
    assert hunt_by_code["GO6800"]["guidebook_season_text"] == "Sept. 9-Oct. 1"
    assert hunt_by_code["MB6202"]["guidebook_public_permits"] == "1"

    token_values = {row["token"] for row in token_rows}
    assert {"800-662-3337", "847411", "DB1500", "EB3158", "$398"}.issubset(token_values)
