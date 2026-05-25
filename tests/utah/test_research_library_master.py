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

    assert len(rows) == 328
    assert summary["record_count"] == 328
    assert summary["source_record_count"] == 328
    assert summary["blocker_count"] == 0

    required = {
        "hunt_code",
        "boundary_id",
        "hunt_code_mapping_status",
        "boundary_id_mapping_status",
        "candidate_hunt_code",
        "candidate_boundary_id",
    }
    assert required.issubset(rows[0])
    assert all(row["hunt_code_mapping_status"] for row in rows)
    assert all(row["boundary_id_mapping_status"] for row in rows)


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
