import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/clear-elk-private-lands-el-lo-2026-permit-fields.py"
SUMMARY = ROOT / "data_truth/permit_overlay_truth/validation/elk_private_lands_EL_LO_2026_cleared_permit_fields_summary.json"
SOURCE_AUDIT = ROOT / "data_truth/permit_overlay_truth/normalized/elk_private_lands_EL_LO_2026_source_audit.csv"

FILES_TO_CHECK = [
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
    ROOT / "processed_data/hunt_master_enriched.csv",
    ROOT / "processed_data/point_ladder_view.csv",
    ROOT / "processed_data/draw_reality_engine_predictive_v2.csv",
    ROOT / "data_model/runtime_drafts/point_ladder_view_v2.csv",
    ROOT / "data/hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "data/hunt-master-canonical-2026-database-candidate.csv",
    ROOT / "processed_data/hunt_master_canonical_2026_SOURCE_OF_TRUTH_FINAL_COMPLETE_NO_PARTIALS.csv",
]

FORBIDDEN_FIELDS = {
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "permit_allotment_2026_res",
    "permit_allotment_2026_nr",
    "permit_allotment_2026_total",
    "public_permits_2026",
    "max_point_permits_2026",
    "random_permits_2026",
    "quota_2026_total",
    "quota_2026_max_pool",
    "quota_2026_random_pool",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def target_codes() -> set[str]:
    return {row["hunt_code"] for row in read_rows(SOURCE_AUDIT)}


def test_el_lo_private_land_rows_have_no_2026_permit_or_quota_leaks() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    codes = target_codes()
    assert len(codes) == 131

    leaks: list[tuple[str, str, str, str]] = []
    for path in FILES_TO_CHECK:
        rows = read_rows(path)
        for row in rows:
            if row.get("hunt_code") not in codes:
                continue
            for field in FORBIDDEN_FIELDS.intersection(row):
                if row.get(field):
                    leaks.append((str(path.relative_to(ROOT)), row["hunt_code"], field, row[field]))

    assert leaks == []
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["target_code_count"] == 131
    assert summary["target_prefix_counts"] == {"EL": 126, "LO": 5}
    assert summary["remaining_numeric_leak_cells"] == 0


def test_public_eb_limited_entry_elk_rows_are_not_cleared() -> None:
    database = read_rows(ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv")
    eb3020 = next(row for row in database if row["hunt_code"] == "EB3020")
    assert eb3020["species"] == "Elk"
    assert eb3020["permits_2026_total"]
    assert eb3020["permit_allotment_2026_total"]
