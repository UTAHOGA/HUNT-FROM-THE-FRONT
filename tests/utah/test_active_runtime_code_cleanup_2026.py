from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "data_truth" / "crosswalk_truth" / "validation" / "active_runtime_codes_removed_2026_summary.json"
ARCHIVE = ROOT / "data_truth" / "crosswalk_truth" / "normalized" / "active_runtime_codes_removed_2026.csv"
HUNT_MASTER = ROOT / "processed_data" / "hunt_master_enriched.csv"
POINT_LADDER = ROOT / "processed_data" / "point_ladder_view.csv"
PREDICTIVE_V2 = ROOT / "processed_data" / "draw_reality_engine_predictive_v2.csv"

RETIRED_CODES = {
    "EA1007",
    "EA1053",
    "EA1287",
    "EA1288",
    "EA1289",
    "EA1290",
    "EA1291",
    "EA1292",
    "EA1293",
    "EA1294",
    "EA1295",
    "EA1296",
    "EA1297",
    "EA1298",
    "EA1299",
    "EA1300",
    "PD1039",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def hunt_codes(path: Path) -> set[str]:
    return {row["hunt_code"] for row in read_rows(path) if row.get("hunt_code")}


def test_current_runtime_surfaces_match_database_cougar_and_retired_guardrails() -> None:
    for path in (HUNT_MASTER, POINT_LADDER):
        codes = hunt_codes(path)
        assert len(codes) == 1449
        assert RETIRED_CODES.isdisjoint(codes)
        assert sorted(code for code in codes if code.startswith("CG")) == ["CG9999"]

    predictive_codes = hunt_codes(PREDICTIVE_V2)
    assert RETIRED_CODES.isdisjoint(predictive_codes)
    assert not [code for code in predictive_codes if code.startswith("CG")]


def test_active_cleanup_archive_preserves_removed_codes() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["artifact"] == "active_runtime_codes_removed_2026"
    assert summary["database_unique_hunt_code_count"] == 1449
    assert summary["database_cougar_codes"] == ["CG9999"]
    assert summary["blocker_count"] == 0
    assert summary["total_removed_archive_row_count"] == 351
    assert set(summary["retired_codes_removed_from_active_surfaces"]) == RETIRED_CODES
    assert len(summary["extra_cougar_codes_removed_from_active_surfaces"]) == 60

    archive_rows = read_rows(ARCHIVE)
    assert len(archive_rows) == 351
    assert {row["hunt_code"] for row in archive_rows if row["removal_reason"] == "USER_CONFIRMED_RETIRED_EFFECTIVE_2026"} == RETIRED_CODES
    archived_cougar_codes = {
        row["hunt_code"]
        for row in archive_rows
        if row["removal_reason"] == "CURRENT_DWR_DATABASE_HAS_SINGLE_STATEWIDE_COUGAR_CODE_CG9999"
    }
    assert len(archived_cougar_codes) == 60
    assert "CG9999" not in archived_cougar_codes
