import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_private_lands_antlerless_elk_rows_are_not_preference_or_bonus() -> None:
    rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\private_lands_antlerless_elk_predictions_v1.csv"))
    assert rows
    assert all(row.get("algorithm_status") != "MODELED_PREFERENCE" for row in rows)
    assert all(row.get("algorithm_status") != "MODELED_BONUS" for row in rows)
