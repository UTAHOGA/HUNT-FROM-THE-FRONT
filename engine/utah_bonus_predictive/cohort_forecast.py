"""Cohort roll-forward for Utah bonus ladders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


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


@dataclass(frozen=True)
class RolloverForecast:
    source_year: int
    retention_rate_raw: float
    retention_rate_smoothed: float
    total_source_applicants: int
    total_unsuccessful_source_applicants: int
    total_rolled_forward_applicants: int
    total_lower_point_additions: int
    total_projected_applicants: int
    applicants_by_points: dict[int, int]


def compute_unsuccessful(total_eligible: int, bonus_permits: int, regular_permits: int) -> int:
    return max(0, int(total_eligible) - int(bonus_permits) - int(regular_permits))


def infer_retention_rate(unsuccessful_prior: int, observed_next: int) -> float:
    return observed_next / max(1, unsuccessful_prior)


def smooth_retention_rate(raw: float, prior: float = 0.85, strength: float = 0.35) -> float:
    smoothed = (1.0 - strength) * raw + strength * prior
    return clamp(smoothed, 0.0, 1.25)


def _eligible(row: Mapping[str, int]) -> int:
    return max(0, int(row.get("eligible", 0)))


def _unsuccessful(row: Mapping[str, int]) -> int:
    return compute_unsuccessful(
        int(row.get("eligible", 0)),
        int(row.get("bonus", 0)),
        int(row.get("regular", 0)),
    )


def infer_group_retention_rate(point_history_by_year: Mapping[int, Mapping[int, Mapping[str, int]]]) -> tuple[float, float]:
    """Infer same-hunt reapply retention from observed unsuccessful cohorts.

    Public point-level data cannot identify individual applicants, so this treats
    the next year's point+1 cohort as the observable proxy for the prior year's
    unsuccessful cohort after reapply/attrition.
    """
    observed_next = 0
    unsuccessful_prior = 0
    years = sorted(point_history_by_year)
    for year in years:
        next_year = year + 1
        if next_year not in point_history_by_year:
            continue
        current = point_history_by_year[year]
        nxt = point_history_by_year[next_year]
        for points, row in current.items():
            unsuccessful = _unsuccessful(row)
            if unsuccessful <= 0:
                continue
            unsuccessful_prior += unsuccessful
            observed_next += _eligible(nxt.get(points + 1, {}))

    raw = infer_retention_rate(unsuccessful_prior, observed_next) if unsuccessful_prior > 0 else 0.85
    return raw, smooth_retention_rate(raw)


def estimate_lower_point_additions(
    point_history_by_year: Mapping[int, Mapping[int, Mapping[str, int]]],
    source_year: int,
    retention_rate: float,
) -> dict[int, int]:
    """Estimate new/switch-in applicants by point level from the latest transition."""
    prior_year = source_year - 1
    if prior_year not in point_history_by_year or source_year not in point_history_by_year:
        return {}

    prior = point_history_by_year[prior_year]
    current = point_history_by_year[source_year]
    additions: dict[int, int] = {}
    candidate_points = set(current) | {point + 1 for point in prior}
    for points in candidate_points:
        observed = _eligible(current.get(points, {}))
        retained_from_prior = 0
        prior_row = prior.get(points - 1)
        if prior_row is not None:
            retained_from_prior = int(round(_unsuccessful(prior_row) * retention_rate))
        additions[points] = max(0, observed - retained_from_prior)
    return additions


def roll_forward_applicant_stack(
    point_history_by_year: Mapping[int, Mapping[int, Mapping[str, int]]],
    source_year: int,
    *,
    retention_rate: float | None = None,
) -> RolloverForecast:
    """Project the next draw year's applicant stack from source-year results.

    Winners are removed from the point stack. Unsuccessful applicants advance one
    point, adjusted by an inferred reapply/retention rate. Lower point additions
    are estimated from the most recent observed transition so the forecast does
    not simply hard-code the prior year's cutoff.
    """
    if source_year not in point_history_by_year:
        raise ValueError(f"source_year {source_year} is not present in point history")

    raw_retention, smoothed_retention = infer_group_retention_rate(point_history_by_year)
    applied_retention = smoothed_retention if retention_rate is None else clamp(retention_rate, 0.0, 1.25)
    source = point_history_by_year[source_year]
    additions = estimate_lower_point_additions(point_history_by_year, source_year, applied_retention)

    projected: dict[int, int] = {}
    total_unsuccessful = 0
    total_rolled = 0
    for points, row in source.items():
        unsuccessful = _unsuccessful(row)
        total_unsuccessful += unsuccessful
        retained = int(round(unsuccessful * applied_retention))
        if retained > 0:
            projected[points + 1] = projected.get(points + 1, 0) + retained
            total_rolled += retained

    for points, count in additions.items():
        if count > 0:
            projected[points] = projected.get(points, 0) + int(count)

    projected = {points: count for points, count in projected.items() if count > 0}
    return RolloverForecast(
        source_year=source_year,
        retention_rate_raw=raw_retention,
        retention_rate_smoothed=applied_retention,
        total_source_applicants=sum(_eligible(row) for row in source.values()),
        total_unsuccessful_source_applicants=total_unsuccessful,
        total_rolled_forward_applicants=total_rolled,
        total_lower_point_additions=sum(additions.values()),
        total_projected_applicants=sum(projected.values()),
        applicants_by_points=projected,
    )

