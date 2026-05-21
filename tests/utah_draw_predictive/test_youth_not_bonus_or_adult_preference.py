import csv
from pathlib import Path

from engine.utah_draw_predictive.classifier import classify_draw_system_type


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_youth_rows_do_not_accidentally_classify_as_bonus_or_adult_preference() -> None:
    youth_deer = {
        "hunt_code": "DB1501",
        "hunt_name": "Box Elder",
        "species": "Deer",
        "sex_type": "Buck",
        "hunt_type": "General Season",
        "hunt_class": "General-season Archery Buck Deer",
        "weapon": "Archery",
        "draw_pool": "youth",
        "source_file": "2025 Youth G.S. Deer Draw Results.pdf",
    }
    youth_elk = {
        "hunt_code": "EB1011",
        "hunt_name": "Youth General Season Bull Elk",
        "species": "Elk",
        "sex_type": "Bull",
        "hunt_type": "General Season - Youth",
        "hunt_class": "General-season Bull Elk",
        "weapon": "Any Legal Weapon",
        "source_file": "DATABASE.csv",
    }
    assert classify_draw_system_type(youth_deer) != "PREFERENCE_GENERAL_SEASON_BUCK_DEER"
    assert classify_draw_system_type(youth_elk) not in {"BONUS_OIL_BIG_GAME", "BONUS_LE_BIG_GAME", "BONUS_PLE_BIG_GAME"}


def test_youth_artifact_rows_do_not_use_bonus_or_preference_fields() -> None:
    rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\youth_draw_predictions_v1.csv"))
    assert all((row.get("p_bonus_pool") or "").strip() == "" for row in rows)
    assert all((row.get("p_random_pool") or "").strip() == "" for row in rows)
    assert all((row.get("p_preference_draw") or "").strip() == "" for row in rows)
