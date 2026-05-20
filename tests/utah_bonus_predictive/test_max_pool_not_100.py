from engine.utah_bonus_predictive.monte_carlo import combine_probabilities


def display_probability_percent(row: dict) -> float | None:
    if row.get("p_draw_pct") is not None:
        return float(row["p_draw_pct"])
    if row.get("p_draw") is not None:
        return float(row["p_draw"]) * 100.0
    return None


def test_status_max_pool_does_not_force_100() -> None:
    row = {"status": "MAX POOL", "p_draw": 0.42}
    assert round(display_probability_percent(row), 3) == 42.0


def test_only_modeled_probability_can_show_100() -> None:
    row = {"status": "MAX POOL", "p_draw": 0.998}
    assert round(display_probability_percent(row), 3) == 99.8
    row2 = {"status": "BEHIND", "p_draw": combine_probabilities(1.0, 0.0)}
    assert round(display_probability_percent(row2), 3) == 100.0

