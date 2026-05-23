from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ML = ROOT / "processed_data" / "ml_draw_predictions_v1.csv"


def row(points: str) -> dict[str, str]:
    with ML.open(newline="", encoding="utf-8-sig") as handle:
        return next(
            r
            for r in csv.DictReader(handle)
            if r["hunt_code"] == "EB3024" and r["residency"] == "Resident" and r["points"] == points
        )


def test_eb3024_resident_has_max_mixed_random_zone_behavior() -> None:
    p30 = row("30")
    p29 = row("29")
    p28 = row("28")
    assert p30["point_pool_zone"] == "max_pool_guaranteed"
    assert p30["p_max_pool_mean"] == "1.000000"
    assert p29["point_pool_zone"] == "max_pool_cutoff_mixed"
    assert p29["projected_applicants"] == "21"
    assert p29["p_max_pool_mean"] == "0.142857"
    assert p28["point_pool_zone"] == "random_pool"
    assert p28["p_random_mean"]


def test_2025_historical_random_success_not_copied_to_2026_prediction() -> None:
    p12 = row("12")
    assert p12["display_odds_text"] != "~1 in 49.0 or 2.0%"
    assert p12["display_odds_text"].startswith("~1 in ")
