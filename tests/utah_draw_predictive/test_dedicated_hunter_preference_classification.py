from engine.utah_draw_predictive.classifier import classify_draw_system_type, sanitize_modeled_probability_fields


def test_dedicated_hunter_classification() -> None:
    row = {"hunt_type": "General Season", "species": "Deer", "sex_type": "Buck", "weapon": "Dedicated Hunter"}
    assert classify_draw_system_type(row) == "PREFERENCE_DEDICATED_HUNTER_DEER"


def test_dedicated_hunter_pending_row_does_not_keep_false_odds() -> None:
    row = sanitize_modeled_probability_fields(
        {
            "hunt_type": "General Season",
            "species": "Deer",
            "sex_type": "Buck",
            "weapon": "Dedicated Hunter",
            "source_dataset": "predictive",
            "p_draw": "0.500000",
            "p_draw_pct": "50.000",
        }
    )
    assert row["algorithm_status"] == "IN_SCOPE_MODEL_PENDING"
    assert row["p_draw"] == ""
    assert row["p_draw_pct"] == ""


def test_dedicated_hunter_modeled_preference_row_keeps_modeled_odds() -> None:
    row = sanitize_modeled_probability_fields(
        {
            "hunt_type": "General Season",
            "species": "Deer",
            "sex_type": "Buck",
            "weapon": "Dedicated Hunter",
            "source_dataset": "predictive",
            "model_strategy": "preference_dedicated_hunter_deer",
            "preference_model_valid": "TRUE",
            "p_preference_draw": "0.625000",
            "p_draw": "0.625000",
            "p_draw_pct": "62.500",
        }
    )
    assert row["algorithm_status"] == "MODELED_PREFERENCE"
    assert row["p_preference_draw"] == "0.625000"
    assert row["p_draw"] == "0.625000"
    assert row["p_draw_pct"] == "62.500"
