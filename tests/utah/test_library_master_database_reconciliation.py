import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "reconcile-library-master-to-database-2026.py"
SUMMARY = ROOT / "processed_data" / "library_master_database_reconciliation_summary.json"
RECON = ROOT / "processed_data" / "library_master_database_reconciliation.csv"
ENRICHED = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "library-master.reconciled.csv"


def test_library_master_reconciliation_outputs_are_built():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    assert SUMMARY.exists()
    assert RECON.exists()
    assert ENRICHED.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["library_record_count"] == 328
    assert summary["database_record_count"] == 1411
    assert summary["database_unique_hunt_codes"] == 1411
    assert summary["record_type_counts"]["document"] == 10
    assert summary["record_type_counts"]["permit_allocation"] == 318


def test_reconciled_candidate_carries_database_fields():
    with ENRICHED.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 328
    assert "database_hunt_code" in rows[0]
    assert "database_match_status" in rows[0]
    assert any(row["database_match_status"].startswith("MATCH") for row in rows)
    assert any(row["database_match_status"] == "DOCUMENT_ROW_NOT_HUNT_CODED" for row in rows)
