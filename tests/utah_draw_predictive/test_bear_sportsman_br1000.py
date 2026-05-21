import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_br1000_is_sportsman_black_bear_not_bear_bonus() -> None:
    ml_rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\ml_draw_predictions_v1.csv"))
    br1000 = [row for row in ml_rows if row.get("hunt_code") == "BR1000"]
    assert br1000
    assert all(row.get("draw_system_type") == "SPORTSMAN_PERMIT" for row in br1000)
    assert all((row.get("p_bonus_pool") or "").strip() == "" for row in br1000)
    assert all((row.get("p_random_pool") or "").strip() == "" for row in br1000)
    assert all((row.get("p_preference_draw") or "").strip() == "" for row in br1000)
