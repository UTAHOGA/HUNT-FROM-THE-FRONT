import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_mountain_lion_rows_do_not_use_bonus_draw_fields() -> None:
    rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\mountain_lion_availability_predictions_v1.csv"))
    assert rows
    assert all(row.get("algorithm_status") == "MODELED_AVAILABILITY" for row in rows)
    assert all((row.get("p_bonus_pool") or "").strip() == "" for row in rows)
    assert all((row.get("p_random_pool") or "").strip() == "" for row in rows)
    assert all((row.get("p_draw") or "").strip() == "" for row in rows)
    assert all((row.get("p_draw_pct") or "").strip() == "" for row in rows)
