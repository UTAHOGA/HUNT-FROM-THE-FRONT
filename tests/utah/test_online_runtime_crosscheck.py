from __future__ import annotations

import csv
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
PROCESSED = REPO / "processed_data"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _group_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        str(row.get("hunt_code") or "").strip().upper(),
        "Nonresident" if str(row.get("residency") or "").strip().lower() == "nonresident" else "Resident",
        (str(row.get("draw_pool") or "").strip().lower() or "standard"),
    )


def test_online_runtime_crosscheck_passes() -> None:
    report = json.loads((PROCESSED / "online_runtime_crosscheck.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["missing_groups_after"]["ladder"] == 0
    assert report["missing_groups_after"]["master"] == 0
    assert report["missing_groups_after"]["reference"] == 0
    assert report["duplicate_keys"]["ladder_hunt_residency_points_draw_pool"] == 0
    assert report["duplicate_keys"]["master_hunt_residency_points_draw_pool"] == 0
    assert report["duplicate_keys"]["reference_hunt_residency_draw_pool"] == 0
    assert report["engine_group_count"] > 0
    assert report["families_promoted_online"]["sportsman_groups"] > 0
    assert report["families_promoted_online"]["mountain_lion_groups"] > 0


def test_runtime_files_include_predictive_only_groups() -> None:
    master_rows = _read_csv(PROCESSED / "hunt_master_enriched.csv")
    ladder_rows = _read_csv(PROCESSED / "point_ladder_view.csv")
    reference_rows = _read_csv(PROCESSED / "hunt_unit_reference_linked.csv")

    master_groups = {_group_key(row) for row in master_rows}
    ladder_groups = {_group_key(row) for row in ladder_rows}
    reference_groups = {_group_key(row) for row in reference_rows}

    expected_groups = {
        ("BI1000", "Resident", "sportsman"),
        ("BR1000", "Resident", "sportsman"),
        ("CG0001", "Resident", "standard"),
        ("DB1770", "Resident", "dedicated_hunter"),
        ("EB1007", "Resident", "youth"),
    }

    assert expected_groups.issubset(master_groups)
    assert expected_groups.issubset(reference_groups)
    assert expected_groups.issubset(ladder_groups)
