from __future__ import annotations

from engine.utah_predictive_mixed.rollover import rollover_applicant_stack, rollover_probability_from_pools


def test_rollover_advances_unsuccessful_applicants_one_point() -> None:
    stack = rollover_applicant_stack([
        {"points": "28", "eligible_applicants": "10", "total_permits": "3"},
        {"points": "0", "eligible_applicants": "20", "total_permits": "0"},
    ])
    assert stack[29]["nonwinners"] == 7
    assert stack[29]["rolled"] > 0
    assert stack[0]["new_entrants"] == 2


def test_mixed_pool_formula_combines_max_and_random() -> None:
    p, reasons = rollover_probability_from_pools("0.30", "0.10")
    assert abs((p or 0) - 0.37) < 1e-9
    assert "ROLLOVER_ADJUSTED_PROBABILITY_USED" in reasons
