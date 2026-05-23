from __future__ import annotations

from engine.utah_predictive_mixed.prior_year import clamp, to_float


def demand_adjustment_factor(demand_pressure_signal: object) -> tuple[float, list[str]]:
    signal = to_float(demand_pressure_signal)
    if signal is None:
        return 1.0, ["NO_HARVEST_FEATURE_ADJUSTMENT"]
    if signal >= 75:
        return 0.95, ["HIGH_DEMAND_HARVEST_SIGNAL", "HARVEST_DEMAND_ADJUSTMENT_APPLIED"]
    if signal >= 65:
        return 0.975, ["MODERATE_DEMAND_HARVEST_SIGNAL", "HARVEST_DEMAND_ADJUSTMENT_APPLIED"]
    if signal <= 15:
        return 1.05, ["LOW_DEMAND_HARVEST_SIGNAL", "HARVEST_DEMAND_ADJUSTMENT_APPLIED"]
    if signal <= 25:
        return 1.025, ["LOW_DEMAND_HARVEST_SIGNAL", "HARVEST_DEMAND_ADJUSTMENT_APPLIED"]
    return 1.0, ["HARVEST_DEMAND_NEUTRAL"]


def harvest_adjusted_probability(p_rollover: float | None, harvest_row: dict[str, str]) -> tuple[float | None, list[str]]:
    if p_rollover is None:
        return None, ["NO_HARVEST_FEATURE_ADJUSTMENT"]
    factor, reasons = demand_adjustment_factor(harvest_row.get("demand_pressure_signal"))
    return clamp(p_rollover * factor), reasons
