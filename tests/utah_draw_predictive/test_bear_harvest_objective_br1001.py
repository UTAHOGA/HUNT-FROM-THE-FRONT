import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_br1001_is_harvest_objective_availability_not_draw_odds() -> None:
    ml_rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\ml_draw_predictions_v1.csv"))
    br1001 = [row for row in ml_rows if row.get("hunt_code") == "BR1001"]
    assert br1001
    assert all(row.get("bear_draw_subtype") == "HARVEST_OBJECTIVE_AVAILABILITY" for row in br1001)
    assert all((row.get("p_draw") or "").strip() == "" for row in br1001)
    assert all((row.get("p_bonus_pool") or "").strip() == "" for row in br1001)
    assert all((row.get("p_random_pool") or "").strip() == "" for row in br1001)
