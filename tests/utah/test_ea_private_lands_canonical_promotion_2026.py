import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROMOTION_SCRIPT = ROOT / "scripts" / "promote-ea-private-lands-canonical-2026.py"
VALIDATION_SCRIPT = ROOT / "scripts" / "validate-ea-private-lands-canonical-2026.py"
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
AUDIT = (
    ROOT
    / "data_truth"
    / "permit_overlay_truth"
    / "validation"
    / "elk_antlerless_private_lands_EA_2026_promotion_audit.csv"
)
PROMOTION_SUMMARY = (
    ROOT
    / "data_truth"
    / "permit_overlay_truth"
    / "validation"
    / "elk_antlerless_private_lands_EA_2026_promotion_summary.json"
)
VALIDATION_SUMMARY = (
    ROOT
    / "data_truth"
    / "permit_overlay_truth"
    / "validation"
    / "elk_antlerless_private_lands_EA_2026_summary.json"
)

CANONICAL_TOTALS = {
    "EA2012": "400",
    "EA2015": "100",
    "EA2016": "275",
    "EA2027": "300",
    "EA2046": "25",
}

CHECK_FILES = [
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv",
    ROOT / "processed_data" / "hunt_master_enriched.csv",
    ROOT / "processed_data" / "draw_reality_engine_predictive_v2.csv",
    ROOT / "processed_data" / "point_ladder_view.csv",
    ROOT / "processed_data" / "all_rac_2026_permits_vs_DATABASE.csv",
    ROOT / "data_truth" / "draw_results_truth" / "validation" / "2026_antlerless_hunt_code_reconciliation.csv",
]


def run_scripts():
    subprocess.run([sys.executable, str(PROMOTION_SCRIPT)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(VALIDATION_SCRIPT)], cwd=ROOT, check=True)


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def rows_by_code(path):
    rows = read_csv(path)
    by_code = {}
    for row in rows:
        by_code.setdefault(row.get("hunt_code"), []).append(row)
    return by_code


def assert_current_total_fields_match(row, expected):
    for field in (
        "permits_2026_total",
        "permit_allotment_2026_total",
        "quota_2026_total",
        "permits_allotted",
        "repo_permits_2026_total",
        "db_permits_2026_total",
        "permits_2026_total_allotted",
    ):
        if field in row and row[field] not in ("", None):
            assert row[field] == expected


def test_ea_private_lands_promotion_updates_database_and_audit_outputs():
    run_scripts()
    assert AUDIT.exists()
    assert PROMOTION_SUMMARY.exists()

    summary = json.loads(PROMOTION_SUMMARY.read_text(encoding="utf-8"))
    assert summary["canonical_hunt_codes"] == 27
    assert summary["canonical_total_permits_2026"] == 9830
    assert "changed_cells_by_file" in summary
    assert summary["verified_database_current_cells"] == 54
    assert summary["failed_database_verification_cells"] == 0
    assert read_csv(AUDIT)

    by_code = rows_by_code(DATABASE)
    for code, expected in CANONICAL_TOTALS.items():
        assert by_code[code][0]["permits_2026_total"] == expected
        assert by_code[code][0]["permit_allotment_2026_total"] == expected
        assert by_code[code][0]["permit_allotment_2026_status"] == "CANONICAL_EA_PRIVATE_LANDS_TOTAL_ONLY"


def test_ea_private_lands_promotion_clears_database_mismatches():
    run_scripts()
    summary = json.loads(VALIDATION_SUMMARY.read_text(encoding="utf-8"))
    assert summary["database_missing_count"] == 0
    assert summary["database_mismatch_count"] == 0
    assert summary["database_mismatch_codes"] == []


def test_ea_private_lands_active_surfaces_do_not_carry_stale_totals():
    run_scripts()
    for path in CHECK_FILES:
        by_code = rows_by_code(path)
        for code, expected in CANONICAL_TOTALS.items():
            for row in by_code.get(code, []):
                assert_current_total_fields_match(row, expected)
