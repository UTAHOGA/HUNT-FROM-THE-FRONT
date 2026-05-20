from engine.utah_draw_predictive.classifier import classify_draw_system_type, resolve_algorithm_status, sanitize_modeled_probability_fields


def test_private_lands_only_antlerless_elk_is_in_scope_model_pending() -> None:
    row = {"hunt_type": "General Season - Private Land Only", "species": "Elk", "sex_type": "Antlerless", "hunt_name": "Private Lands Only Antlerless Elk"}
    assert classify_draw_system_type(row) == "PRIVATE_LANDS_ONLY_ANTLERLESS_ELK"
    assert resolve_algorithm_status(row) == "IN_SCOPE_MODEL_PENDING"


def test_private_lands_only_antlerless_elk_does_not_receive_fake_preference_draw_odds() -> None:
    row = sanitize_modeled_probability_fields(
        {
            "hunt_type": "General Season - Private Land Only",
            "species": "Elk",
            "sex_type": "Antlerless",
            "hunt_name": "Private Lands Only Antlerless Elk",
            "source_dataset": "predictive",
            "p_draw": "0.500000",
            "p_draw_pct": "50.000",
        }
    )
    assert row["algorithm_status"] == "IN_SCOPE_MODEL_PENDING"
    assert row["p_draw"] == ""
    assert row["p_draw_pct"] == ""
    assert row["draw_outlook"] == "MODEL PENDING"
