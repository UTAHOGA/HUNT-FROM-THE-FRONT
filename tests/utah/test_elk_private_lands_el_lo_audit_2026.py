import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit-elk-private-lands-el-lo-2026.py"
NORMALIZED = ROOT / "data_truth/permit_overlay_truth/normalized/elk_private_lands_EL_LO_2026_source_audit.csv"
DB_COMPARE = ROOT / "data_truth/permit_overlay_truth/validation/elk_private_lands_EL_LO_2026_vs_DATABASE.csv"
RAC_CANDIDATES = ROOT / "data_truth/permit_overlay_truth/validation/elk_private_lands_EL_LO_2026_rac_candidate_matches.csv"
SUMMARY = ROOT / "data_truth/permit_overlay_truth/validation/elk_private_lands_EL_LO_2026_summary.json"


def run_script() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_el_lo_source_has_expected_rows_dates_and_blank_permits() -> None:
    run_script()
    rows = read_csv(NORMALIZED)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert len(rows) == 131
    assert summary["prefix_counts"] == {"EL": 126, "LO": 5}
    assert summary["source_numeric_rows"] == 0
    assert summary["date_context_counts"]["HAS_2025_DATE_ONLY"] == 125
    assert summary["date_context_counts"]["CROSSES_2025_2026"] == 1
    assert summary["date_context_counts"]["HAS_2026_DATE"] == 5


def test_attached_source_does_not_support_numeric_database_promotion() -> None:
    run_script()
    comparison = read_csv(DB_COMPARE)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["database_missing_rows"] == 0
    assert summary["database_numeric_not_in_source_count"] == 128
    assert not [row for row in comparison if row["comparison_status"] == "NUMERIC_MISMATCH"]
    assert {row["hunt_code"] for row in comparison if row["comparison_status"] == "SOURCE_AND_DATABASE_BLANK"} == {
        "LO0012",
        "LO0013",
        "LO0014",
    }


def test_rac_matches_are_evidence_only_and_not_exact_private_land_codes() -> None:
    run_script()
    candidates = read_csv(RAC_CANDIDATES)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["rac_exact_code_matches"] == 0
    assert summary["rac_prefix_candidate_matches"] > 0
    assert all(row["promotion_status"] == "REVIEW_EVIDENCE_ONLY" for row in candidates)
    assert {row["match_type"] for row in candidates} == {"EL_TO_EB_PREFIX_CANDIDATE"}
