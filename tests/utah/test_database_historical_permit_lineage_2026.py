import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit-database-historical-permit-lineage-2026.py"
OUTPUT = ROOT / "processed_data" / "database_historical_permit_lineage_2026.csv"
SUMMARY = ROOT / "processed_data" / "database_historical_permit_lineage_2026_summary.json"
VALIDATION = (
    ROOT
    / "data_truth"
    / "comparison_outputs"
    / "validation"
    / "database_historical_permit_lineage_2026_summary.json"
)


def run_audit():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_database_historical_permit_lineage_outputs_are_written():
    run_audit()
    assert OUTPUT.exists()
    assert SUMMARY.exists()
    assert VALIDATION.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["database_row_count"] == 1394
    assert summary["output_row_count"] == 2788
    assert summary["historical_years_detected"] == ["2025"]
    assert summary["lineage_blocker_count"] == 0
    assert summary["canonical_historical_source_truth_rows"] == 1600
    assert summary["historical_2025_full_permit_universe_rows"] == 1028
    assert summary["historical_2025_bonus_point_draw_subset_rows"] == 572
    assert summary["historical_2025_non_bonus_or_general_subset_rows"] == 456
    assert "narrower bonus-point draw-results subset" in summary["guardrail"]
    assert "must not drift" in summary["guardrail"]


def test_database_historical_permit_lineage_confirms_2025_source_coverage():
    run_audit()
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    permit_counts = summary["family_canonical_status_counts"]["permits_2025"]
    draw_counts = summary["family_canonical_status_counts"]["permits_2025_draw"]
    assert permit_counts["CANONICAL_HISTORICAL_SOURCE_TRUTH"] == 1028
    assert permit_counts["NO_HISTORICAL_VALUE"] == 366
    assert draw_counts["CANONICAL_HISTORICAL_SOURCE_TRUTH"] == 572
    assert draw_counts["NO_HISTORICAL_VALUE"] == 822

    permit_sources = summary["family_source_value_counts"]["permits_2025"]
    draw_sources = summary["family_source_value_counts"]["permits_2025_draw"]
    assert permit_sources["2025_DRAW_RESULTS_TABLES"] == 1028
    assert draw_sources["canonical_2026_source_of_truth_draw_results"] == 572


def test_database_historical_permit_lineage_has_no_paired_family_strays():
    run_audit()
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["paired_family_compare_counts"] == {
        "BOTH_BLANK": 366,
        "MATCH": 572,
        "PRIMARY_ONLY": 456,
    }

    with OUTPUT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert not [row for row in rows if row["canonical_status"] == "BLOCKED_LINEAGE_REPAIR_REQUIRED"]
    assert not [row for row in rows if row["paired_family_compare_status"] == "MISMATCH"]
