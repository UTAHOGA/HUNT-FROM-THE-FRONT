import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_bear_rows_never_use_preference_fields() -> None:
    rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\bear_draw_predictions_v1.csv"))
    assert rows
    assert all((row.get("p_preference_draw") or "").strip() == "" for row in rows)
