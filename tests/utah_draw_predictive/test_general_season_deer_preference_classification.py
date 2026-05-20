from engine.utah_draw_predictive.classifier import classify_draw_system_type, sanitize_modeled_probability_fields


def test_general_season_deer_preference_classification() -> None:
    row = {"hunt_type": "General Season", "hunt_class": "General-season Muzzleloader Buck Deer", "species": "Deer", "sex_type": "Buck"}
    assert classify_draw_system_type(row) == "PREFERENCE_GENERAL_SEASON_BUCK_DEER"


def test_general_season_deer_classified_not_modeled_does_not_keep_false_odds() -> None:
    row = sanitize_modeled_probability_fields(
        {
            "hunt_type": "General Season",
            "hunt_class": "General-season Muzzleloader Buck Deer",
            "species": "Deer",
            "sex_type": "Buck",
            "source_dataset": "predictive",
            "p_draw": "0.500000",
            "p_draw_pct": "50.000",
        }
    )
    assert row["algorithm_status"] == "IN_SCOPE_MODEL_PENDING"
    assert row["p_draw"] == ""
    assert row["p_draw_pct"] == ""


def test_general_season_deer_modeled_preference_row_keeps_modeled_odds() -> None:
    row = sanitize_modeled_probability_fields(
        {
            "hunt_type": "General Season",
            "hunt_class": "Public",
            "species": "Deer",
            "sex_type": "Buck",
            "source_dataset": "predictive",
            "model_strategy": "preference_general_deer",
            "preference_model_valid": "TRUE",
            "p_draw": "0.625000",
            "p_draw_pct": "62.500",
        }
    )
    assert row["algorithm_status"] == "MODELED_PREFERENCE"
    assert row["p_draw"] == "0.625000"
    assert row["p_draw_pct"] == "62.500"
