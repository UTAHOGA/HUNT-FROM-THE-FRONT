import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "compare-library-master-to-hunt-master-enriched.py"
SUMMARY = ROOT / "processed_data" / "library_master_vs_hunt_master_enriched_summary.json"
DETAIL = ROOT / "processed_data" / "library_master_vs_hunt_master_enriched.csv"


def test_library_master_hunt_master_comparison_outputs_are_built():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    assert SUMMARY.exists()
    assert DETAIL.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["library_record_count"] == 328
    assert summary["hunt_master_row_count"] > 50000
    assert summary["hunt_master_unique_hunt_codes"] >= 1400
    assert summary["library_codes_missing_from_hunt_master"] == 0


def test_library_master_hunt_master_comparison_has_expected_statuses():
    with DETAIL.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 328
    statuses = {row["hunt_master_compare_status"] for row in rows}
    assert "DOCUMENT_ROW_NOT_HUNT_CODED" in statuses
    assert any(status.startswith("FOUND") for status in statuses)
