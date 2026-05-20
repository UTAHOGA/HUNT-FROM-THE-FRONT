from engine.utah_draw_predictive.classifier import classify_draw_system_type, sanitize_modeled_probability_fields


def test_private_cwmu_rows_do_not_model_as_bonus() -> None:
    row = {
        "hunt_type": "CWMU",
        "hunt_class": "Private",
        "species": "Deer",
        "sex_type": "Buck",
        "hunt_name": "Private Creek CWMU",
        "source_dataset": "predictive",
        "p_draw": "0.500000",
        "p_draw_pct": "50.000",
    }
    assert classify_draw_system_type(row) == "LANDOWNER_BIG_GAME"
    sanitized = sanitize_modeled_probability_fields(dict(row))
    assert sanitized["algorithm_status"] == "EXCLUDED_NOT_PREDICTIVE_DRAW"
    assert sanitized["p_draw"] == ""
    assert sanitized["p_draw_pct"] == ""
