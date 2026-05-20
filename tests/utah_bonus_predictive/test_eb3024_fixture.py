from engine.utah_bonus_predictive.cohort_forecast import (
    compute_unsuccessful,
    infer_retention_rate,
)
from engine.utah_bonus_predictive.monte_carlo import compute_bonus_pool_probability


def test_eb3024_2024_resident_bonus_pool() -> None:
    # 2024 resident fixture.
    applicants = {29: 1, 28: 9}
    p29, above29, _ = compute_bonus_pool_probability(29, applicants, max_point_permits=4)
    p28, above28, _ = compute_bonus_pool_probability(28, applicants, max_point_permits=4)
    assert above29 == 0
    assert p29 == 1.0
    assert above28 == 1
    assert round(p28, 6) == 0.333333
    assert compute_unsuccessful(9, 3, 0) == 6


def test_eb3024_2025_resident_bonus_pool_and_retention() -> None:
    applicants = {30: 1, 29: 5}
    p30, above30, _ = compute_bonus_pool_probability(30, applicants, max_point_permits=5)
    p29, above29, _ = compute_bonus_pool_probability(29, applicants, max_point_permits=5)
    assert above30 == 0
    assert p30 == 1.0
    assert above29 == 1
    assert round(p29, 6) == 0.8
    assert round(infer_retention_rate(6, 5), 6) == 0.833333

