import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_private_lands_antlerless_elk_rows_are_modeled_as_allocation() -> None:
    rows = _read_csv(Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\private_lands_antlerless_elk_predictions_v1.csv"))
    assert rows
    assert all(row.get("draw_system_type") == "PRIVATE_LANDS_ONLY_ANTLERLESS_ELK" for row in rows)
    assert all(row.get("algorithm_status") == "MODELED_ALLOCATION" for row in rows)
    assert all((row.get("permits_allotted") or "").strip() != "" for row in rows)
    assert all((row.get("allocation_status") or "").strip() == "ALLOCATION KNOWN / REMAINING UNKNOWN" for row in rows)
    assert all((row.get("availability_status") or "").strip() == "ALLOCATION KNOWN / REMAINING UNKNOWN" for row in rows)
    assert all((row.get("season_status") or "").strip() == "SEASON DATES PRESENT" for row in rows)
    assert all((row.get("private_land_only_flag") or "").strip() == "TRUE" for row in rows)
