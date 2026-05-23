from __future__ import annotations

from collections import defaultdict

from engine.utah_predictive_mixed.prior_year import clamp, to_float


def default_retention_rate(points: int, max_points: int) -> float:
    if points >= max_points - 2:
        return 0.95
    if points >= max_points // 2:
        return 0.90
    if points == 0:
        return 0.70
    return 0.80


def rollover_applicant_stack(prior_rows: list[dict[str, str]]) -> dict[int, dict[str, float]]:
    max_points = max((int(to_float(row.get("points")) or 0) for row in prior_rows), default=0)
    projected: dict[int, dict[str, float]] = defaultdict(lambda: {"rolled": 0.0, "projected": 0.0, "nonwinners": 0.0})
    zero_point_applicants = 0.0
    for row in prior_rows:
        point = int(to_float(row.get("points")) or 0)
        applicants = to_float(row.get("applicants") or row.get("eligible_applicants") or row.get("applicants_at_level")) or 0.0
        success = to_float(row.get("total_permits")) or 0.0
        unsuccessful = max(applicants - success, 0.0)
        retention = default_retention_rate(point, max_points)
        rolled = unsuccessful * retention
        projected[point + 1]["rolled"] += rolled
        projected[point + 1]["projected"] += rolled
        projected[point + 1]["nonwinners"] += unsuccessful
        if point == 0:
            zero_point_applicants = applicants
    new_entrants = max(zero_point_applicants * 0.10, 0.0)
    projected[0]["projected"] += new_entrants
    projected[0]["new_entrants"] = new_entrants
    return dict(projected)


def rollover_probability_from_pools(p_max_pool: object, p_random: object, p_preference: object = None) -> tuple[float | None, list[str]]:
    preference = to_float(p_preference)
    if preference is not None:
        return clamp(preference), ["PREFERENCE_COMPONENT_USED", "ROLLOVER_ADJUSTED_PROBABILITY_USED"]
    max_pool = to_float(p_max_pool)
    random = to_float(p_random)
    if max_pool is None and random is None:
        return None, ["ROLLOVER_COMPONENT_MISSING"]
    max_pool = max_pool or 0.0
    random = random or 0.0
    return clamp(1.0 - ((1.0 - max_pool) * (1.0 - random))), ["ROLLOVER_ADJUSTED_PROBABILITY_USED"]
