import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_public_restricted_pursuit_bear_rows_can_be_modeled_bonus() -> None:
    rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\bear_draw_predictions_v1.csv"))
    modeled = [
        row for row in rows
        if row.get("algorithm_status") == "MODELED_BONUS"
        and row.get("bear_draw_subtype") == "RESTRICTED_BEAR_PURSUIT"
    ]
    assert modeled
    assert all((row.get("p_preference_draw") or "").strip() == "" for row in modeled)
    assert all((row.get("p_bonus_pool") or "").strip() != "" for row in modeled)
    assert all((row.get("p_random_pool") or "").strip() != "" for row in modeled)
