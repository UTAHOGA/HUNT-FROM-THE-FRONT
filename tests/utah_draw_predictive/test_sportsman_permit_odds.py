import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_sportsman_rows_stay_pending_without_usable_odds_source() -> None:
    rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\sportsman_permit_predictions_v1.csv"))
    assert rows
    assert all(row.get("draw_system_type") == "SPORTSMAN_PERMIT" for row in rows)
    assert all(row.get("algorithm_status") == "IN_SCOPE_MODEL_PENDING" for row in rows)
    assert all((row.get("p_draw") or "").strip() == "" for row in rows)
    assert all((row.get("p_bonus_pool") or "").strip() == "" for row in rows)
    assert all((row.get("p_random_pool") or "").strip() == "" for row in rows)
    assert all((row.get("p_preference_draw") or "").strip() == "" for row in rows)
