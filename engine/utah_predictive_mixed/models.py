from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlendWeights:
    prior_year_behavior_weight: float = 0.60
    quota_change_weight: float = 0.20
    applicant_rollover_weight: float = 0.15
    harvest_quality_demand_weight: float = 0.05

    def validate(self) -> None:
        if self.harvest_quality_demand_weight > 0.10:
            raise ValueError("harvest_quality_demand_weight must not exceed 0.10 without a version bump and test.")
        total = (
            self.prior_year_behavior_weight
            + self.quota_change_weight
            + self.applicant_rollover_weight
            + self.harvest_quality_demand_weight
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError("Mixed predictive weights must sum to 1.0.")


@dataclass(frozen=True)
class MixedComponentResult:
    p_prior_year_baseline: float | None
    p_quota_adjusted: float | None
    p_rollover_adjusted: float | None
    p_harvest_adjusted: float | None
    p_draw_mean: float | None
    reason_codes: list[str]
