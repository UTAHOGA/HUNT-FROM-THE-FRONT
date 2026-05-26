from __future__ import annotations

import csv
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
PROCESSED = REPO / "processed_data"

ALLOTMENT_COLUMNS = {
    "permit_allotment_2026_res",
    "permit_allotment_2026_nr",
    "permit_allotment_2026_total",
    "permit_allotment_2026_source",
    "permit_allotment_2026_source_file",
    "permit_allotment_2026_status",
}

RUNTIME_FILES = [
    PROCESSED / "hunt_unit_reference_linked.csv",
    PROCESSED / "hunt_master_enriched.csv",
    PROCESSED / "draw_reality_engine.csv",
    PROCESSED / "point_ladder_view.csv",
    PROCESSED / "ml_draw_predictions_v1.csv",
    PROCESSED / "draw_reality_engine_predictive_v2.csv",
]

REFERENCE_FILES = [
    PROCESSED / "hunt_unit_reference_linked.csv",
    PROCESSED / "hunt_master_enriched.csv",
    PROCESSED / "draw_reality_engine.csv",
    PROCESSED / "point_ladder_view.csv",
]

DATABASE = REPO / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"


def _rows(path: Path, hunt_code: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if str(row.get("hunt_code") or "").upper() == hunt_code.upper()
        ]


def _first_row(path: Path, hunt_code: str, residency: str | None = None) -> dict[str, str]:
    for row in _rows(path, hunt_code):
        if residency is None or row.get("residency") == residency:
            return row
    raise AssertionError(f"Missing {hunt_code} {residency or ''} in {path.name}")


def test_current_year_allotment_columns_exist_in_runtime_files() -> None:
    for path in RUNTIME_FILES:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            header = set(next(csv.reader(handle)))
        assert ALLOTMENT_COLUMNS.issubset(header), path.name


def test_rac_current_year_allotment_overrides_stale_database_values_for_ea1267() -> None:
    required_reference_hits = 0
    for path in RUNTIME_FILES:
        rows = _rows(path, "EA1267")
        if not rows:
            continue
        if path in REFERENCE_FILES:
            required_reference_hits += 1
        row = _first_row(path, "EA1267", "Resident")
        assert row["permit_allotment_2026_res"] == "180"
        assert row["permit_allotment_2026_nr"] == "20"
        assert row["permit_allotment_2026_total"] == "200"
        assert row["permit_allotment_2026_source"] == "2026_RAC_CURRENT_YEAR_ALLOTMENT"
        assert row["permit_allotment_2026_status"] == "RAC_CURRENT_YEAR_SPLIT"
        assert row["permit_allotment_2026_source_file"].endswith("2026_rac_antlerless_elk_permits.csv")
    assert required_reference_hits == len(REFERENCE_FILES)


def test_database_promoted_to_rac_current_year_values_for_ea1267() -> None:
    row = _first_row(DATABASE, "EA1267")
    assert row["permits_2026_res"] == "180"
    assert row["permits_2026_nr"] == "20"
    assert row["permits_2026_total"] == "200"
    assert row["season"] == "Oct 03 2026 - Oct 25 2026"
    assert row["permit_allotment_2026_source"] == "2026_RAC_CURRENT_YEAR_ALLOTMENT"


def test_database_missing_direct_rac_rows_added() -> None:
    ea1287 = _first_row(DATABASE, "EA1287")
    assert ea1287["hunt_name"] == "Box Elder, Grouse Creek"
    assert ea1287["permits_2026_res"] == "27"
    assert ea1287["permits_2026_nr"] == "3"
    assert ea1287["permits_2026_total"] == "30"
    assert ea1287["season"] == "Nov 06 2026 - Jan 31 2027"

    retired_codes = {"EA1007", "EA1053", "PD1039"}
    for code in retired_codes:
        assert not _rows(DATABASE, code)


def test_all_rac_vs_database_audit_zero_numeric_mismatches_after_promotion() -> None:
    report = json.loads((PROCESSED / "all_rac_2026_permits_vs_DATABASE.json").read_text(encoding="utf-8"))
    assert report["rac_hunt_codes_missing_in_database"] == 0
    assert report["numeric_mismatch_rows"] == 0
    assert report["significant_difference_rows_abs_delta_gt_5"] == 0


def test_total_only_current_year_allotment_does_not_invent_residency_split() -> None:
    for path in RUNTIME_FILES:
        row = _first_row(path, "EA2012", "Resident")
        assert row["permit_allotment_2026_res"] == ""
        assert row["permit_allotment_2026_nr"] == ""
        assert row["permit_allotment_2026_total"] == "500"
        assert row["permit_allotment_2026_source"] == "2026_RAC_CURRENT_YEAR_ALLOTMENT"
        assert row["permit_allotment_2026_status"] == "RAC_CURRENT_YEAR_TOTAL_ONLY"
        assert row["permit_allotment_2026_source_file"].endswith(
            "2026_rac_private_lands_only_antlerless_elk_permits.csv"
        )


def test_antlerless_deer_total_only_current_year_allotment_uses_corrected_rac_table() -> None:
    row = _first_row(PROCESSED / "hunt_unit_reference_linked.csv", "DA1009", "Resident")
    assert row["permit_allotment_2026_res"] == ""
    assert row["permit_allotment_2026_nr"] == ""
    assert row["permit_allotment_2026_total"] == "25"
    assert row["permit_allotment_2026_source"] == "2026_RAC_CURRENT_YEAR_ALLOTMENT"
    assert row["permit_allotment_2026_status"] == "RAC_CURRENT_YEAR_TOTAL_ONLY"

    assert _rows(PROCESSED / "hunt_unit_reference_linked.csv", "DA1051") == []


def test_existing_2026_permits_are_fallback_when_no_direct_rac_row_exists() -> None:
    row = _first_row(PROCESSED / "hunt_unit_reference_linked.csv", "BR1008", "Resident")
    assert row["permit_allotment_2026_res"] == row["permits_2026_res"] == "26"
    assert row["permit_allotment_2026_nr"] == row["permits_2026_nr"] == "2"
    assert row["permit_allotment_2026_total"] == row["permits_2026_total"] == "28"
    assert row["permit_allotment_2026_source"] == "FALLBACK_EXISTING_2026_PERMITS"


def test_current_year_allotment_overlay_report_written() -> None:
    report_path = PROCESSED / "current_year_permit_allotment_overlay_write.json"
    summary_path = PROCESSED / "current_year_permit_allotment_overlay_write_summary.csv"
    index_path = PROCESSED / "current_year_permit_allotment_rac_index.csv"
    assert report_path.exists()
    assert summary_path.exists()
    assert index_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["rac_current_year_allotment_source_label"] == "2026_RAC_CURRENT_YEAR_ALLOTMENT"
    assert report["fallback_source_label"] == "FALLBACK_EXISTING_2026_PERMITS"
    assert report["rac_direct_hunt_code_count"] > 500
    assert len(report["target_files"]) == 6
    assert report["totals"]["rows_checked"] > 200000
