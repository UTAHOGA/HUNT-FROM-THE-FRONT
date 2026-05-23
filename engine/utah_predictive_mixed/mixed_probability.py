from __future__ import annotations

from engine.utah_predictive_mixed.models import BlendWeights
from engine.utah_predictive_mixed.prior_year import clamp


def blend_probability(
    p_prior: float | None,
    p_quota: float | None,
    p_rollover: float | None,
    p_harvest: float | None,
    weights: BlendWeights | None = None,
) -> tuple[float | None, list[str]]:
    weights = weights or BlendWeights()
    weights.validate()
    components = [
        (weights.prior_year_behavior_weight, p_prior, "PRIOR_YEAR_WEIGHTED_BASELINE"),
        (weights.quota_change_weight, p_quota, "QUOTA_ADJUSTED_COMPONENT_USED"),
        (weights.applicant_rollover_weight, p_rollover, "ROLLOVER_COMPONENT_USED"),
        (weights.harvest_quality_demand_weight, p_harvest, "HARVEST_COMPONENT_USED"),
    ]
    available = [(weight, value, code) for weight, value, code in components if value is not None]
    if not available:
        return None, ["INSUFFICIENT_DRAW_HISTORY"]
    reason_codes = ["MIXED_MODEL_USED"] + [code for _, _, code in available]
    if len(available) < len(components):
        reason_codes.append("MISSING_COMPONENTS_REWEIGHTED")
    if p_prior is None and p_rollover is not None and len(available) == 2 and p_harvest is not None:
        reason_codes.append("ROLLOVER_ONLY_NEW_HUNT")
    total_weight = sum(weight for weight, _, _ in available)
    return clamp(sum((weight / total_weight) * (value or 0.0) for weight, value, _ in available)), reason_codes


def uncertainty_bands(p_draw_mean: float | None, grade: str) -> tuple[float | None, float | None, float | None, list[str]]:
    if p_draw_mean is None or grade == "F":
        return None, None, None, []
    width = {"A": 0.05, "B": 0.10, "C": 0.15, "D": 0.25}.get(grade, 0.25)
    return clamp(p_draw_mean - width), p_draw_mean, clamp(p_draw_mean + width), [f"UNCERTAINTY_BAND_{grade if grade in {'A','B','C','D'} else 'D'}"]


def format_display_odds(p_draw_mean: float | None) -> tuple[str, str]:
    if p_draw_mean is None:
        return "", "Not available"
    if p_draw_mean <= 0:
        return "0.0", "Not available"
    pct = p_draw_mean * 100.0
    return f"{pct:.1f}", f"~1 in {1.0 / p_draw_mean:.1f} or {pct:.1f}%"
