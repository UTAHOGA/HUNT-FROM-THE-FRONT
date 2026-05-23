from __future__ import annotations

from engine.utah_predictive_mixed.harvest_features import harvest_adjusted_probability
from engine.utah_predictive_mixed.mixed_probability import format_display_odds, uncertainty_bands


def test_harvest_adjustment_cannot_change_probability_by_more_than_five_percent() -> None:
    high, _ = harvest_adjusted_probability(0.50, {"demand_pressure_signal": "90"})
    low, _ = harvest_adjusted_probability(0.50, {"demand_pressure_signal": "10"})
    assert high == 0.475
    assert low == 0.525


def test_uncertainty_bands_and_display_odds_format() -> None:
    p10, p50, p90, reasons = uncertainty_bands(0.5, "A")
    assert (p10, p50, p90) == (0.45, 0.5, 0.55)
    assert "UNCERTAINTY_BAND_A" in reasons
    pct, text = format_display_odds(0.5)
    assert pct == "50.0"
    assert text == "~1 in 2.0 or 50.0%"
