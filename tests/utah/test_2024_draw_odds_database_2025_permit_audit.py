from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "data_truth/draw_results_truth/validation/draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits_summary.json"
PROMOTION_SUMMARY = ROOT / "data_truth/draw_results_truth/validation/draw_odds_2024_blank_2025_permits_promoted_summary.json"
NORMALIZED = ROOT / "data_truth/draw_results_truth/normalized/draw_odds_2024_model_target_2025_permit_totals.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"


def _csv_by_code(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {row["hunt_code"]: row for row in csv.DictReader(handle)}


def test_2024_draw_odds_audit_is_reference_only_not_overwrite_instruction() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["source_rows"] == 874
    assert summary["source_unique_hunt_codes"] == 874
    assert summary["source_codes_missing_database_count"] == 53
    assert summary["permits_2025_status_counts"] == {
        "DIFFERS": 448,
        "MATCH": 373,
        "SOURCE_CODE_NOT_IN_DATABASE": 53,
    }
    assert summary["permits_2025_draw_status_counts"] == {
        "DATABASE_BLANK": 222,
        "DIFFERS": 277,
        "MATCH": 322,
        "SOURCE_CODE_NOT_IN_DATABASE": 53,
    }
    assert summary["safe_blank_candidate_codes"] == []
    assert "No DATABASE.csv permit fields are modified" in summary["guardrail"]


def test_2024_draw_odds_parser_ignores_odds_ratio_numbers() -> None:
    rows = _csv_by_code(NORMALIZED)
    row = rows["BI6503"]

    assert row["resident_total_permits"] == "9"
    assert row["nonresident_total_permits"] == "1"
    assert row["total_public_draw_permits"] == "10"


def test_2025_database_broad_fields_are_filled_only_for_safe_blank_candidates() -> None:
    summary = json.loads(PROMOTION_SUMMARY.read_text(encoding="utf-8"))
    database_rows = _csv_by_code(DATABASE)
    broad_populated = [
        row for row in database_rows.values() if row.get("permits_2025_total", "").strip()
    ]

    assert summary["candidate_count"] == 2
    assert summary["promoted_row_count"] == 2
    assert summary["promoted_codes"] == ["EB3168", "MB6265"]
    assert len(database_rows) == 1394
    assert len(broad_populated) == 1030
    assert (
        database_rows["EB3168"]["permits_2025_res"],
        database_rows["EB3168"]["permits_2025_nr"],
        database_rows["EB3168"]["permits_2025_total"],
        database_rows["EB3168"]["permits_2025_source"],
    ) == ("2", "1", "3", "2024_DRAW_ODDS_MODEL_TARGET_2025_BLANK_FILL")
