import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_mountain_lion_rows_do_not_use_preference_fields() -> None:
    rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\mountain_lion_availability_predictions_v1.csv"))
    assert rows
    assert all((row.get("p_preference_draw") or "").strip() == "" for row in rows)
    assert all((row.get("draw_system_type") or "").strip() == "MOUNTAIN_LION_DRAW" for row in rows)
