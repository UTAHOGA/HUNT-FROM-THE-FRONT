from __future__ import annotations

from engine.utah_predictive_mixed.mixed_probability import blend_probability
from engine.utah_predictive_mixed.models import BlendWeights


def test_default_weights_equal_required_contract() -> None:
    weights = BlendWeights()
    assert weights.prior_year_behavior_weight == 0.60
    assert weights.quota_change_weight == 0.20
    assert weights.applicant_rollover_weight == 0.15
    assert weights.harvest_quality_demand_weight == 0.05
    weights.validate()


def test_prior_year_component_carries_highest_weight() -> None:
    weights = BlendWeights()
    assert weights.prior_year_behavior_weight > weights.quota_change_weight
    assert weights.prior_year_behavior_weight > weights.applicant_rollover_weight
    assert weights.prior_year_behavior_weight > weights.harvest_quality_demand_weight


def test_missing_components_are_reweighted_proportionally() -> None:
    p, reasons = blend_probability(0.50, None, 0.25, None)
    expected = ((0.60 / 0.75) * 0.50) + ((0.15 / 0.75) * 0.25)
    assert abs((p or 0) - expected) < 1e-9
    assert "MISSING_COMPONENTS_REWEIGHTED" in reasons
