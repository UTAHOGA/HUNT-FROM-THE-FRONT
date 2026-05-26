import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/fill-database-boundary-ids-from-json-2026.py"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
AUDIT = ROOT / "data_truth/crosswalk_truth/validation/database_boundary_id_fill_2026_audit.csv"
SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/database_boundary_id_fill_2026_summary.json"

EXPECTED = {
    "EA1287": "867",
    "EA1288": "952",
    "EA1289": "952",
    "EA1290": "952",
    "EA1291": "950",
    "EA1292": "950",
    "EA1293": "140",
    "EA1294": "951",
    "EA1295": "224",
    "EA1296": "227",
    "EA1297": "953",
    "EA1299": "845",
    "EA1300": "845",
    "EA1298": "954",
}

RETIRED_EFFECTIVE_2026 = {"EA1007", "EA1053", "PD1039"}


def run_script():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_boundary_fill_promotes_all_blank_database_rows_from_exact_sources():
    run_script()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["blocker_count"] == 0
    assert summary["blank_boundary_id_before"] == 0 or summary["blank_boundary_id_before"] == 17
    assert summary["blank_boundary_id_after"] == 0
    assert summary["unresolved_count"] == 0
    assert summary["duplicate_hunt_code_count"] == 0

    database_rows = {row["hunt_code"]: row for row in read_rows(DATABASE)}
    for code in RETIRED_EFFECTIVE_2026:
        assert code not in database_rows

    for code, boundary_id in EXPECTED.items():
        assert database_rows[code]["boundary_id"] == boundary_id

    assert all(row["boundary_id"] for row in database_rows.values())


def test_boundary_fill_audit_has_mapping_law_evidence():
    run_script()
    audit_rows = {row["hunt_code"]: row for row in read_rows(AUDIT)}

    for code, boundary_id in EXPECTED.items():
        row = audit_rows[code]
        assert row["promoted_boundary_id"] == boundary_id
        assert row["candidate_boundary_id"] == boundary_id
        assert row["boundary_id_mapping_status"] in {
            "REVIEWED_BOUNDARY_ID_CONFIRMED",
            "REVIEWED_BOUNDARY_ID_PROMOTED",
            "REVIEWED_BOUNDARY_ID_CORRECTED",
        }
        assert row["source_file"]
        assert row["source_sha256"]

    for code in RETIRED_EFFECTIVE_2026:
        assert code not in audit_rows

    assert audit_rows["EA1299"]["match_method"] == "EXACT_OFFICIAL_BOUNDARY_NAME_JSON"
    assert audit_rows["EA1288"]["match_method"] == "EXACT_UNIQUE_DWR_BOUNDARY_GEOJSON_NAME"
