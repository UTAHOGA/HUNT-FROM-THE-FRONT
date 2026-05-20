"""Cohort roll-forward for Utah bonus ladders."""

from __future__ import annotations

from dataclasses import dataclass


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass(frozen=True)
class CohortCarryForward:
    unsuccessful_at_level: int
    retention_rate_raw: float
    retention_rate_smoothed: float
    projected_retained_applicants: float
    projected_switch_in_applicants: float
    projected_switch_out_applicants: float


def compute_unsuccessful(total_eligible: int, bonus_permits: int, regular_permits: int) -> int:
    return max(0, int(total_eligible) - int(bonus_permits) - int(regular_permits))


def infer_retention_rate(unsuccessful_prior: int, observed_next: int) -> float:
    return observed_next / max(1, unsuccessful_prior)


def smooth_retention_rate(raw: float, prior: float = 0.85, strength: float = 0.35) -> float:
    smoothed = (1.0 - strength) * raw + strength * prior
    return clamp(smoothed, 0.0, 1.25)

