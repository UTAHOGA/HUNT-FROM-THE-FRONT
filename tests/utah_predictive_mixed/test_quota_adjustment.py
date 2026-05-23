from __future__ import annotations

import csv
from pathlib import Path

from engine.utah_predictive_mixed.quota import quota_adjusted_probability, quota_for_row


ROOT = Path(__file__).resolve().parents[2]
ML = ROOT / "processed_data" / "ml_draw_predictions_v1.csv"


def rows() -> list[dict[str, str]]:
    with ML.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def row(hunt_code: str, residency: str, points: str) -> dict[str, str]:
    return next(r for r in rows() if r["hunt_code"] == hunt_code and r["residency"] == residency and r["points"] == points)


def test_2026_official_quota_is_used_when_present() -> None:
    eb3022 = row("EB3022", "Resident", "7")
    quota, reasons = quota_for_row(eb3022)
    assert quota["quota_source_status"] == "official"
    assert quota["quota_source_year"] == "2026"
    assert quota["quota_2026_total"] == "130"
    assert "OFFICIAL_2026_QUOTA_USED" in reasons


def test_quota_adjustment_caps_and_codes() -> None:
    p, ratio, reasons = quota_adjusted_probability(0.5, 10, 100)
    assert p == 1.0
    assert ratio == 2.0
    assert "QUOTA_RATIO_CAPPED_HIGH" in reasons
