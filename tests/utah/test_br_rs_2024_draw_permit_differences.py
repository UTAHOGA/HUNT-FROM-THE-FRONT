from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIFF_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "br_rs_2024_model_target_2025_permit_differences.csv"
)
SUMMARY_JSON = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "br_rs_2024_model_target_2025_permit_differences_summary.json"
)
PROMOTION_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "br_rs_2024_draw_pdf_values_promoted_to_DATABASE_2025.csv"
)
PROMOTION_SUMMARY_JSON = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "br_rs_2024_draw_pdf_values_promoted_to_DATABASE_2025_summary.json"
)
SOURCE_ONLY_PROMOTION_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "source_only_br_2024_draw_pdf_values_promoted_to_DATABASE_2025.csv"
)
SOURCE_ONLY_PROMOTION_SUMMARY_JSON = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "source_only_br_2024_draw_pdf_values_promoted_to_DATABASE_2025_summary.json"
)
IMPORT_MANIFEST_CSV = (
    ROOT
    / "data_truth/harvest_results_truth/raw_inventory/"
    / "imported_rm_sheep_2024_harvest_source.csv"
)
IMPORT_MANIFEST_JSON = (
    ROOT
    / "data_truth/harvest_results_truth/raw_inventory/"
    / "imported_rm_sheep_2024_harvest_source_summary.json"
)
RM_SHEEP_PDF = (
    ROOT
    / "pipeline/RAW/hunt_unit_database/2025/pdf/harvest_report/rocky mountain sheep/"
    / "r.m. sheep 2024 harvest by unit.pdf"
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_br_rs_difference_summary_is_stable() -> None:
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    rows = _read_csv(DIFF_CSV)

    assert summary["difference_row_count"] == 0
    assert summary["numeric_difference_count"] == 0
    assert summary["status_counts"] == {}
    assert summary["prefix_counts"] == {}
    assert summary["source_codes_missing_database"] == []
    assert len(rows) == 0


def test_br_rs_pdf_promotion_replaced_active_numeric_differences() -> None:
    summary = json.loads(PROMOTION_SUMMARY_JSON.read_text(encoding="utf-8"))
    rows = {row["hunt_code"]: row for row in _read_csv(PROMOTION_CSV)}

    assert summary["promoted_row_count"] == 63
    assert summary["prefix_counts"] == {"BR": 55, "RS": 8}
    assert summary["skipped_missing_database_codes"] == ["BR7008", "BR7019", "BR7108", "BR7208"]

    assert rows["BR7004"]["before_permits_2025_total"] == "20"
    assert rows["BR7004"]["after_permits_2025_total"] == "8"
    assert rows["BR7004"]["after_permits_2025_draw_total"] == "8"

    assert rows["RS6703"]["after_permits_2025_total"] == rows["RS6703"]["after_permits_2025_draw_total"]


def test_source_only_bear_codes_are_promoted_as_2025_history_only() -> None:
    summary = json.loads(SOURCE_ONLY_PROMOTION_SUMMARY_JSON.read_text(encoding="utf-8"))
    rows = {row["hunt_code"]: row for row in _read_csv(SOURCE_ONLY_PROMOTION_CSV)}

    assert summary["inserted_row_count"] == 4
    assert summary["inserted_codes"] == ["BR7008", "BR7019", "BR7108", "BR7208"]

    assert rows["BR7008"]["boundary_id"] == "684"
    assert rows["BR7008"]["source_total_permits"] == "43"
    assert rows["BR7019"]["boundary_id"] == "610"
    assert rows["BR7019"]["source_total_permits"] == "5"
    assert "2025 historical draw rows" in summary["guardrail"]


def test_rm_sheep_harvest_pdf_import_manifest_matches_file() -> None:
    summary = json.loads(IMPORT_MANIFEST_JSON.read_text(encoding="utf-8"))
    rows = _read_csv(IMPORT_MANIFEST_CSV)

    assert RM_SHEEP_PDF.exists()
    digest = hashlib.sha256(RM_SHEEP_PDF.read_bytes()).hexdigest()

    assert summary["imported_source_count"] == 1
    assert summary["source_sha256"] == digest
    assert rows[0]["source_sha256"] == digest
    assert rows[0]["promotion_status"] == "IMPORTED_NOT_EXTRACTED"
    assert rows[0]["source_class"] == "harvest_results"
