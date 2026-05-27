import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.json"
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"


def _read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _row_by_code(path: Path, hunt_code: str):
    rows = _read_csv(path)
    return next(row for row in rows if row["hunt_code"] == hunt_code)


def _source_row(hunt_code: str):
    rows = json.loads(SOURCE.read_text(encoding="utf-8"))
    return next(row for row in rows if row["hunt_code"] == hunt_code)


def test_database_db1002_uses_explicit_2025_draw_permits():
    row = _row_by_code(DATABASE, "DB1002")

    assert row["permits_2025_res"] == "1"
    assert row["permits_2025_nr"] == "0"
    assert row["permits_2025_total"] == "1"
    assert row["permits_2025_source"] == "2025_DRAW_RESULTS_TABLES"

    assert row["permits_2025_draw_res"] == "1"
    assert row["permits_2025_draw_nr"] == "0"
    assert row["permits_2025_draw_total"] == "1"
    assert row["draw_2025_bg_report_page"] == "19"


def test_database_2026_allotment_not_overwritten_by_2025_draw_promotion():
    row = _row_by_code(DATABASE, "DB1002")

    assert row["permit_allotment_2026_res"] == "1"
    assert row["permit_allotment_2026_nr"] == "0"
    assert row["permit_allotment_2026_total"] == "1"


def test_database_2025_draw_fields_match_canonical_source_for_all_promoted_codes():
    source_rows = {
        row["hunt_code"]: row
        for row in json.loads(SOURCE.read_text(encoding="utf-8"))
        if row.get("permits_2025_draw_total") not in {None, ""}
    }
    db_rows = {row["hunt_code"]: row for row in _read_csv(DATABASE)}

    assert len(source_rows) == 572
    assert set(source_rows).issubset(db_rows)
    for hunt_code, source in source_rows.items():
        database = db_rows[hunt_code]
        assert database["permits_2025_draw_res"] == str(source.get("permits_2025_draw_res", "")).strip()
        assert database["permits_2025_draw_nr"] == str(source.get("permits_2025_draw_nr", "")).strip()
        assert database["permits_2025_draw_total"] == str(source.get("permits_2025_draw_total", "")).strip()


def test_database_2025_permit_fields_come_from_draw_results_tables():
    expected = {
        "DB1002": ("1", "0", "1"),
        "EB3024": ("9", "1", "10"),
        "EA1010": ("18", "2", "20"),
        "PB5025": ("39", "4", "43"),
        "BR1008": ("26", "2", "28"),
    }
    for hunt_code, (res, nr, total) in expected.items():
        row = _row_by_code(DATABASE, hunt_code)
        assert row["permits_2025_res"] == res
        assert row["permits_2025_nr"] == nr
        assert row["permits_2025_total"] == total
        assert row["permits_2025_source"] == "2025_DRAW_RESULTS_TABLES"


def test_2025_draw_results_promotion_report_zero_draw_field_mismatches():
    report = json.loads((ROOT / "processed_data" / "permits_2025_draw_results_promotion_report.json").read_text())

    assert report["source_hunt_codes"] == 1028
    assert report["draw_field_total_mismatch_count"] == 0
    assert report["source_file"] == "pipeline/RAW/hunt_unit_database/2026/csv/draw_results_long_cumulative_2025_draw_folder_DATABASE_ALIGNED_V3.csv"


def test_2025_prior_generation_reconciliation_confirms_17_new_blank_2025_hunts():
    report = json.loads((ROOT / "processed_data" / "permits_2025_prior_generation_reconciliation.json").read_text())

    assert report["prior_generation_hunt_code_count"] == 1394
    assert report["active_database_hunt_code_count"] == 1411
    assert report["active_not_in_prior_count"] == 17
    assert report["new_2026_gap_codes_match_active_not_prior"] is True
    for surface in report["surface_checks"]:
        assert surface["missing_required_columns_or_json_fields"] == []
        assert surface["missing_json_keys_count"] == 0
        assert surface["new_2026_hunts_with_nonblank_2025_count"] == 0


def test_runtime_reference_surfaces_carry_db1002_2025_draw_fields():
    for rel_path in [
        "processed_data/hunt_master_enriched_2026_draw_subset.csv",
        "processed_data/hunt_unit_reference_linked.csv",
        "processed_data/point_ladder_view.csv",
        "processed_data/draw_reality_engine.csv",
        "processed_data/draw_reality_engine_predictive_v2.csv",
        "processed_data/ml_draw_predictions_v1.csv",
    ]:
        rows = [row for row in _read_csv(ROOT / rel_path) if row.get("hunt_code") == "DB1002"]
        assert rows, rel_path
        assert all(row.get("permits_2025_draw_res") == "1" for row in rows)
        assert all(row.get("permits_2025_draw_nr") == "0" for row in rows)
        assert all(row.get("permits_2025_draw_total") == "1" for row in rows)


def test_2025_draw_permit_promotion_report_written():
    report = json.loads((ROOT / "processed_data" / "permits_2025_draw_field_promotion_report.json").read_text())

    assert report["source_hunt_codes_with_2025_draw_permits"] == 572
    assert report["files_written"] >= 10
    assert any(row["file"] == "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv" for row in report["results"])


def test_ambiguous_permits_year_columns_removed_from_active_surfaces():
    ambiguous = {"permits_year_res", "permits_year_nr", "permits_year_total"}
    for rel_path in [
        "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
        "processed_data/hunt_master_enriched.csv",
        "processed_data/hunt_unit_reference_linked.csv",
        "processed_data/point_ladder_view.csv",
        "processed_data/draw_reality_engine.csv",
    ]:
        with (ROOT / rel_path).open(newline="", encoding="utf-8-sig") as handle:
            headers = set(csv.DictReader(handle).fieldnames or [])
        assert not (headers & ambiguous), rel_path


def test_permits_year_column_removal_report_written():
    report = json.loads((ROOT / "processed_data" / "permits_year_column_removal_report.json").read_text())

    assert report["removed_fields"] == ["permits_year_res", "permits_year_nr", "permits_year_total"]
    assert report["db1002_spot_check"]["permits_2025_draw_total"] == "1"
    assert report["db1002_spot_check"]["permit_allotment_2026_total"] == "1"


def test_database_has_no_empty_or_unpopulated_draw_2025_species_section_columns():
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        headers = csv.DictReader(handle).fieldnames or []

    assert "" not in headers
    assert "draw_2025_species_section" not in headers


def test_database_has_no_blank_rows_or_missing_hunt_codes():
    rows = _read_csv(DATABASE)

    assert rows
    assert all(any(str(value).strip() for value in row.values()) for row in rows)
    assert all(row.get("hunt_code", "").strip() for row in rows)
    assert len(rows) == 1449
    assert len({row["hunt_code"] for row in rows}) == 1449


def test_empty_database_column_removal_report_written():
    report = json.loads((ROOT / "processed_data" / "empty_database_column_removal_report.json").read_text())
    database_check = report["database_column_check"]

    assert report["drop_fields"] == ["<blank_header>", "draw_2025_species_section"]
    assert report["total_blank_rows_removed"] == 0
    assert database_check["database_rows"] == 1411
    assert database_check["database_unique_hunt_codes"] == 1411
    assert database_check["blank_header_count"] == 0
    assert database_check["has_draw_2025_species_section"] is False
    assert database_check["fully_blank_rows"] == 0
    assert database_check["missing_hunt_code_nonblank_rows"] == 0
