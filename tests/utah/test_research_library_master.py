import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build-research-library-master.py"
MASTER = ROOT / "data_truth/research_library_truth/normalized/research_library_master.csv"
SUMMARY = ROOT / "data_truth/research_library_truth/validation/research_library_master_summary.json"
GAPS = ROOT / "data_truth/research_library_truth/validation/research_library_master_mapping_gaps.csv"
PROCESSED = ROOT / "processed_data/research_library_master.csv"


def run_builder():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_research_library_master_builds_with_required_mapping_contract():
    run_builder()

    assert MASTER.exists()
    assert SUMMARY.exists()
    assert GAPS.exists()
    assert PROCESSED.exists()

    rows = read_rows(MASTER)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert len(rows) == 447
    assert summary["record_count"] == 447
    assert summary["source_record_count"] == 447
    assert summary["source_catalog_record_count"] == 328
    assert summary["feeder_file_record_count"] == 119
    assert summary["direct_dwr_hunt_planner_csv_files_discovered"] == 89
    assert summary["direct_dwr_hunt_planner_csv_feeder_rows"] == 88
    assert summary["blocker_count"] == 0

    required = {
        "hunt_code",
        "boundary_id",
        "hunt_code_mapping_status",
        "boundary_id_mapping_status",
        "candidate_hunt_code",
        "candidate_boundary_id",
        "source_filename_years",
        "source_path_years",
        "source_file_modified_utc",
        "permit_allotment_2026_promotion_status",
    }
    assert required.issubset(rows[0])
    assert all(row["hunt_code_mapping_status"] for row in rows)
    assert all(row["boundary_id_mapping_status"] for row in rows)
    assert any(row["source_role"] == "CANONICAL_DATABASE" for row in rows)
    assert any(row["source_role"] == "ENRICHED_RUNTIME_REFERENCE" for row in rows)
    assert any(row["source_role"] == "POINT_LADDER_REFERENCE" for row in rows)


def test_research_library_master_keeps_old_candidate_codes_out_of_truth_fields():
    run_builder()
    rows = read_rows(MASTER)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    permit_rows = [row for row in rows if row["record_type"] == "permit_allocation"]
    document_rows = [row for row in rows if row["record_type"] == "document"]

    assert len(permit_rows) == 318
    assert len(document_rows) == 10
    assert summary["candidate_hunt_code_rows"] == 318
    assert summary["candidate_hunt_code_unique_count"] == 147
    assert summary["feeder_file_record_count"] == 119
    assert summary["canonical_database_feeder_rows"] == 1
    assert summary["boundary_alignment_feeder_rows"] == 118
    assert summary["feeder_files_missing"] == []
    assert summary["permit_allotment_2026_promotion_status_counts"]["NOT_PROMOTED_SOURCE_REGISTRY_ONLY"] == 119
    assert summary["permit_allotment_2026_promotion_status_counts"]["NOT_PROMOTED_CATALOG_REVIEW_REQUIRED"] == 328
    assert summary["reviewed_hunt_code_rows"] == 0
    assert summary["reviewed_boundary_id_rows"] == 0
    assert summary["candidate_codes_missing_database"] == []
    assert summary["candidate_codes_missing_hunt_master"] == []

    assert all(row["hunt_code"] == "" for row in permit_rows)
    assert all(row["boundary_id"] == "" for row in permit_rows)
    assert all(row["candidate_hunt_code"] for row in permit_rows)
    assert all(row["candidate_boundary_id"] for row in permit_rows)
    assert all(row["hunt_code_mapping_status"] == "HISTORICAL_PREFIX_REVIEW_REQUIRED" for row in permit_rows)
    assert all(row["hunt_code_mapping_status"] == "DOCUMENT_LEVEL_MAPPING_REQUIRED" for row in document_rows)


def test_research_library_master_registers_boundary_alignment_feeders():
    run_builder()
    rows = read_rows(MASTER)

    feeders = [row for row in rows if row["record_type"] == "feeder_file"]
    by_id = {row["source_record_id"]: row for row in feeders}

    assert by_id["feeder_database_2026_canonical"]["source_role"] == "CANONICAL_DATABASE"
    assert by_id["feeder_database_2026_canonical"]["boundary_alignment_role"] == "PRIMARY_BOUNDARY_ID_SOURCE"
    assert by_id["feeder_database_2026_canonical"]["source_row_count"] == "1411"
    assert by_id["feeder_database_2026_canonical"]["source_unique_hunt_codes"] == "1411"
    assert int(by_id["feeder_database_2026_canonical"]["source_unique_boundary_ids"]) > 0

    assert by_id["feeder_hunt_master_enriched"]["source_role"] == "ENRICHED_RUNTIME_REFERENCE"
    assert by_id["feeder_hunt_master_enriched"]["source_unique_hunt_codes"] == "1471"
    assert by_id["feeder_point_ladder_view"]["source_role"] == "POINT_LADDER_REFERENCE"
    assert by_id["feeder_statewide_composite_boundaries_geojson"]["source_role"] == "BOUNDARY_GEOJSON_REFERENCE"
    assert by_id["feeder_statewide_composite_boundaries_geojson"]["source_file_status"] == "FOUND"
    assert by_id["feeder_rac_recommended_permits_2026_xlsx"]["source_role"] == "CURRENT_YEAR_PERMIT_RECOMMENDATION"
    assert by_id["feeder_rac_recommended_permits_2026_xlsx"]["source_sheet_count"] == "1"
    assert by_id["feeder_rac_recommended_permits_2026_pdf"]["source_role"] == "CURRENT_YEAR_PERMIT_RECOMMENDATION"
    assert by_id["feeder_rac_recommended_permits_2026_pdf"]["source_page_count"] == "39"
    assert by_id["feeder_preliminary_bg_harvest_2025_pdf"]["source_role"] == "PRELIMINARY_HARVEST_REPORT"
    assert by_id["feeder_preliminary_bg_harvest_2025_pdf"]["source_page_count"] == "23"


def test_direct_dwr_hunt_planner_csv_folder_is_registered_without_permit_promotion():
    run_builder()
    rows = read_rows(MASTER)
    feeders = [row for row in rows if row["record_type"] == "feeder_file"]
    direct_csv_rows = [row for row in feeders if row["source_record_id"].startswith("feeder_dwr_csv_")]

    assert len(direct_csv_rows) == 88
    assert all(row["source_file_status"] == "FOUND" for row in direct_csv_rows)
    assert all(row["permit_allotment_2026_promotion_status"] == "NOT_PROMOTED_SOURCE_REGISTRY_ONLY" for row in direct_csv_rows)
    assert all(row["source_file_modified_utc"] for row in direct_csv_rows)

    by_id = {row["source_record_id"]: row for row in feeders}
    hunt_matrix = by_id["feeder_dwr_csv_2026_utah_dwr_hunt_matrix"]
    assert hunt_matrix["source_unique_hunt_codes"] == "1394"
    assert int(hunt_matrix["source_unique_boundary_ids"]) > 0

    draw_2025 = by_id["feeder_dwr_csv_draw_results_long_cumulative_2025_draw_folder_database_aligned_v3"]
    assert "2025" in draw_2025["source_filename_years"]
    assert draw_2025["source_role"] == "DWR_HUNT_PLANNER_DRAW_RESULT_CSV"
    assert draw_2025["permit_allotment_2026_promotion_status"] == "NOT_PROMOTED_SOURCE_REGISTRY_ONLY"
    assert "Do not promote 2025 permit values" in draw_2025["permit_allotment_2026_promotion_notes"]
