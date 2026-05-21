import csv
from pathlib import Path

from engine.utah_draw_predictive.classifier import classify_draw_system_type


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_youth_general_any_bull_elk_rows_classify_separately() -> None:
    row = {
        "hunt_code": "EB1011",
        "hunt_name": "Youth General Season Bull Elk",
        "species": "Elk",
        "sex_type": "Bull",
        "hunt_type": "General Season - Youth",
        "hunt_class": "General-season Bull Elk",
        "weapon": "Any Legal Weapon",
        "draw_pool": "standard",
        "source_file": "DATABASE.csv",
    }
    assert classify_draw_system_type(row) == "YOUTH_GENERAL_ANY_BULL_ELK"


def test_youth_general_any_bull_elk_rows_stay_pending_without_fake_odds() -> None:
    rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\youth_draw_predictions_v1.csv"))
    elk_rows = [row for row in rows if row.get("draw_system_type") == "YOUTH_GENERAL_ANY_BULL_ELK"]
    assert elk_rows
    assert all(row.get("algorithm_status") == "IN_SCOPE_MODEL_PENDING" for row in elk_rows)
    assert all((row.get("p_draw") or "").strip() == "" for row in elk_rows)
    assert all((row.get("p_draw_pct") or "").strip() == "" for row in elk_rows)
