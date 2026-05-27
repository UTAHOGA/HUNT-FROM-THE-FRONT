from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
SUMMARY = ROOT / "data_truth" / "comparison_outputs" / "validation" / "hunt_class_selection_matrix_2026_summary.json"
DETAIL = ROOT / "data_truth" / "comparison_outputs" / "validation" / "hunt_class_selection_matrix_2026.csv"
HUNT_MASTER_DUPLICATE = ROOT / "processed_data" / "hunt_master_enriched_2026_draw_subset.csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _by_code(path: Path) -> dict[str, dict[str, str]]:
    return {row["hunt_code"]: row for row in _read_csv(path) if row.get("hunt_code")}


def test_selection_matrix_order_is_species_sex_hunt_type_hunt_class_weapon() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["selection_matrix"] == ["species", "sex_type", "hunt_type", "hunt_class", "weapon"]
    assert summary["internal_engine_field"] == "draw_2026_system_type"
    assert summary["removed_duplicate_fields"] == ["draw_2026_permit_family"]
    assert summary["database_hunt_class_populated_count"] == 1288


def test_database_has_hunt_class_without_duplicate_draw_family_column() -> None:
    rows = _by_code(DATABASE)
    headers = set(rows["EB1007"])

    assert "hunt_class" in headers
    assert "draw_2026_permit_family" not in headers

    assert rows["EB1007"]["hunt_type"] == "General Season - Any Bull"
    assert rows["EB1007"]["hunt_class"] == "Youth"
    assert rows["EB1007"]["weapon"] == "Any Legal Weapon"

    assert rows["EB1003"]["hunt_type"] == "General Season - Spike Bull"
    assert rows["EB1003"]["hunt_class"] == "Spike Only"

    assert rows["EB3022"]["hunt_type"] == "Limited Entry"
    assert rows["EB3022"]["hunt_class"] == "Mature Bull"
    assert rows["EB3022"]["draw_2026_system_type"] == "BONUS_LE_BIG_GAME"

    assert rows["DB1002"]["hunt_type"] == "Premium Limited Entry"
    assert rows["DB1002"]["hunt_class"] == "Premium Limited Entry"


def test_hunt_master_duplicate_has_hunt_class_selection_layer() -> None:
    rows = _by_code(HUNT_MASTER_DUPLICATE)

    assert rows["EB1007"]["hunt_class"] == "Youth"
    assert rows["EB3022"]["hunt_class"] == "Mature Bull"
    assert rows["EA2012"]["hunt_type"] == "Private Lands Only"
    assert rows["EA2012"]["hunt_class"] == "Antlerless"


def test_selection_matrix_detail_export_matches_database() -> None:
    db_rows = _by_code(DATABASE)
    detail_rows = _by_code(DETAIL)

    assert detail_rows["EB1007"]["hunt_class"] == db_rows["EB1007"]["hunt_class"]
    assert detail_rows["EB1007"]["hunt_type"] == db_rows["EB1007"]["hunt_type"]
    assert detail_rows["EB3022"]["hunt_class"] == db_rows["EB3022"]["hunt_class"]
