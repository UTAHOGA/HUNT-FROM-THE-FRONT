"""Monte Carlo random-pool model using Utah bonus weighting."""

from __future__ import annotations

import random
from collections import defaultdict


def simulate_random_pool_probability(points: int, applicants_by_points: dict[int, int], random_permits: int, iterations: int = 5000, seed: int = 2026) -> float:
    if random_permits <= 0:
        return 0.0
    rng = random.Random(seed)
    hits = 0
    for _ in range(iterations):
        ladder = []
        target_index = None
        idx = 0
        for p, count in sorted(applicants_by_points.items(), reverse=True):
            for i in range(max(0, int(count))):
                draws = p + 1
                score = min(rng.random() for _ in range(draws))
                ladder.append((score, idx))
                if p == points and i == 0 and target_index is None:
                    target_index = idx
                idx += 1
        if target_index is None:
            continue
        ladder.sort(key=lambda x: x[0])
        selected = {entry[1] for entry in ladder[:random_permits]}
        if target_index in selected:
            hits += 1
    return hits / iterations if iterations else 0.0


def compute_bonus_pool_probability(points: int, applicants_by_points: dict[int, int], max_point_permits: int) -> tuple[float, int, int]:
    applicants_above = sum(v for p, v in applicants_by_points.items() if p > points)
    at_level = max(0, int(applicants_by_points.get(points, 0)))
    remaining = max_point_permits - applicants_above
    if max_point_permits <= 0 or remaining <= 0 or at_level <= 0:
        return 0.0, applicants_above, at_level
    if remaining >= at_level:
        return 1.0, applicants_above, at_level
    return remaining / at_level, applicants_above, at_level


def combine_probabilities(p_bonus_pool: float, p_random_pool: float) -> float:
    return 1.0 - ((1.0 - p_bonus_pool) * (1.0 - p_random_pool))

