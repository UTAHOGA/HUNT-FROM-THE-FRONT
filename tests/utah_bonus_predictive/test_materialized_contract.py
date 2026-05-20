import csv
from pathlib import Path

from engine.utah_bonus_predictive.materialize import write_csv


def test_rows_keyed_by_hunt_code_residency_points(tmp_path: Path) -> None:
    rows = [
        {"hunt_code": "EB3024", "residency": "Resident", "points": 28, "p_draw": 0.5, "p_draw_pct": 50.0},
        {"hunt_code": "EB3024", "residency": "Nonresident", "points": 28, "p_draw": 0.1, "p_draw_pct": 10.0},
    ]
    path = tmp_path / "draw_reality_engine.csv"
    write_csv(path, rows, ["hunt_code", "residency", "points", "p_draw", "p_draw_pct"])
    out = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len({(r["hunt_code"], r["residency"], r["points"]) for r in out}) == 2
    assert all(0.0 <= float(r["p_draw"]) <= 1.0 for r in out)
    assert all(0.0 <= float(r["p_draw_pct"]) <= 100.0 for r in out)

