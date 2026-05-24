from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "processed_data/2023_big_game_field_regulations_source_audit.json"
TEXT_LINES = ROOT / "data_truth/regulations_truth/normalized/2023_big_game_field_regulations_text_lines.csv"
NUMBER_TOKENS = ROOT / "data_truth/regulations_truth/normalized/2023_big_game_field_regulations_number_tokens.csv"
EXPECTED_TEXT_CHECKS = (
    ROOT / "data_truth/regulations_truth/normalized/2023_big_game_field_regulations_expected_text_checks.csv"
)


def _run_audit() -> None:
    subprocess.run([sys.executable, "scripts/audit-big-game-field-regulations-2023.py"], cwd=ROOT, check=True)


def test_2023_field_regulations_source_audit_passes() -> None:
    _run_audit()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["source_file"] == "pipeline/RAW/hunt_unit_database/2023/pdf/regulation/2023_field_regs.pdf"
    assert summary["expected_title"] == "2023 Utah Big Game Field Regulations"
    assert summary["expected_source_year"] == "2023"
    assert summary["actual_sha256"] == "c68a0ef12e09e810449e2a5f569bcf445709249c9354036bc1ef17086477284f"
    assert summary["classification"] == "REGULATION_REFERENCE_ONLY"
    assert summary["modeling_guardrail"] == "DO_NOT_USE_AS_DRAW_ODDS_HARVEST_FEATURE_OR_2026_QUOTA_INPUT"
    assert summary["database_reconciliation_effect"] == "NO_DRAW_OR_PREDICTION_ROWS_PROMOTED"
    assert summary["pdf_page_count"] == 72
    assert summary["text_line_count"] == 4014
    assert summary["number_token_count"] == 1582
    assert summary["token_type_counts"] == {"number_or_money": 1286, "code_citation": 191, "date": 105}
    assert summary["expected_text_check_count"] == 69
    assert summary["expected_text_check_failures"] == 0
    assert summary["audit_blocker_count"] == 0
    assert all(summary["checks"].values())


def test_2023_field_regulations_line_and_token_audits_are_materialized() -> None:
    _run_audit()

    with TEXT_LINES.open(newline="", encoding="utf-8-sig") as handle:
        line_rows = list(csv.DictReader(handle))
    with NUMBER_TOKENS.open(newline="", encoding="utf-8-sig") as handle:
        token_rows = list(csv.DictReader(handle))
    with EXPECTED_TEXT_CHECKS.open(newline="", encoding="utf-8-sig") as handle:
        check_rows = list(csv.DictReader(handle))

    assert len(line_rows) == 4014
    assert len(token_rows) == 1582
    assert len(check_rows) == 69
    assert {row["status"] for row in check_rows} == {"PASS"}

    lines_by_page: dict[str, list[str]] = {}
    for row in line_rows:
        lines_by_page.setdefault(row["printed_page"], []).append(row["line_text"])

    assert any("General archery deer Aug. 19-Sept. 15" in line for line in lines_by_page["7"])
    assert any("General deer $40 $398" in line for line in lines_by_page["9"])
    assert any("July 11: General-season archery elk" in line for line in lines_by_page["15"])
    assert any("Antlerless elk permits may be used only during" in line for line in lines_by_page["39"])
    assert any("Youth means someone who is 17 years old or" in line for line in lines_by_page["71"])

    token_values = {row["token"] for row in token_rows}
    assert {"800-662-3337", "847411", "R657-5-23", "R657-5-48", "$398"}.issubset(token_values)
