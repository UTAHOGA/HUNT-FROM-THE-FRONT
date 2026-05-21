import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_db1007_is_not_sportsman_without_alias_source_proof() -> None:
    rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\sportsman_permit_predictions_v1.csv"))
    assert not any(row.get("hunt_code") == "DB1007" for row in rows)
