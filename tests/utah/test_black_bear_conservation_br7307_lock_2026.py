from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "lock-black-bear-conservation-br7307-2026.py"
LOCK_CSV = ROOT / "data_truth" / "permit_overlay_truth" / "normalized" / "black_bear_conservation_BR7307_lock_2026.csv"
AUDIT_CSV = (
    ROOT
    / "data_truth"
    / "permit_overlay_truth"
    / "validation"
    / "black_bear_conservation_BR7307_lock_2026_audit.csv"
)
SUMMARY_JSON = ROOT / "processed_data" / "black_bear_conservation_BR7307_lock_2026_summary.json"
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"

SURFACES = [
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv",
    ROOT / "processed_data" / "hunt_master_enriched.csv",
    ROOT / "processed_data" / "draw_reality_engine.csv",
    ROOT / "processed_data" / "point_ladder_view.csv",
    ROOT / "processed_data" / "draw_reality_engine_predictive_v2.csv",
    ROOT / "processed_data" / "bear_draw_predictions_v1.csv",
    ROOT / "processed_data" / "bear_predictions_v1.csv",
    ROOT / "data_model" / "runtime_drafts" / "point_ladder_view_v2.csv",
    ROOT / "data_model" / "runtime_drafts" / "mixed_predictive_engine_2026.materialized.csv",
    ROOT / "data_model" / "runtime_drafts" / "mixed_predictive_engine_2026.predictions.csv",
]


def run_lock():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def br7307_rows(path: Path):
    return [row for row in read_rows(path) if row.get("hunt_code") == "BR7307"]


def test_br7307_lock_script_runs_and_records_pdf_total():
    run_lock()
    assert LOCK_CSV.exists()
    assert AUDIT_CSV.exists()
    assert SUMMARY_JSON.exists()

    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    assert summary["hunt_code"] == "BR7307"
    assert summary["selected_total"] == 4
    assert summary["pdf_evidence_row_count"] == 4
    assert summary["pdf_evidence_total_if_summed"] == 4
    assert summary["normalized_conservation_source_row_count"] == 3
    assert summary["normalized_conservation_source_total_if_summed"] == 4
    assert summary["failed_database_verification_cells"] == 0
    assert summary["validation_error_count"] == 0

    lock_row = read_rows(LOCK_CSV)[0]
    assert lock_row["Total"] == "4"
    assert lock_row["source_row_count"] == "4"
    assert lock_row["source_rows_total_if_summed"] == "4"


def test_br7307_database_is_total_only_conservation_reference():
    run_lock()
    row = br7307_rows(DATABASE)[0]
    assert row["hunt_name"] == "La Sal"
    assert row["species"] == "Black Bear"
    assert row["weapon"] == "Multiseason"
    assert row["hunt_type"] == "Multiseason - Conservation"
    assert row["permits_2026_res"] == ""
    assert row["permits_2026_nr"] == ""
    assert row["permits_2026_total"] == "4"
    assert row["permit_allotment_2026_total"] == "4"
    assert row["permit_allotment_2026_status"] == "TOTAL_ONLY"


def test_br7307_current_surfaces_have_no_zero_or_blank_2026_total():
    run_lock()
    for path in SURFACES:
        rows = br7307_rows(path)
        assert rows, path
        for row in rows:
            for field in ("permits_2026_total", "permit_allotment_2026_total", "public_permits_2026", "quota_2026_total"):
                if field in row:
                    assert row[field] == "4", (path, field, row[field])
            if "permit_status" in row:
                assert row["permit_status"] in ("TOTAL_ONLY", "")
            if "modeled_by_engine" in row:
                assert row["modeled_by_engine"] == "False"
