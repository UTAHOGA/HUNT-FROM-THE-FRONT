from engine.utah_draw_predictive.classifier import classify_draw_system_type, sanitize_modeled_probability_fields


def test_remaining_turkey_row_does_not_receive_draw_odds() -> None:
    row = {
        "hunt_code": "TK1999",
        "hunt_name": "Central Area remaining permit",
        "species": "Turkey",
        "sex_type": "Bearded",
        "hunt_type": "Limited Entry",
        "draw_pool": "remaining",
        "p_draw": "0.25",
        "p_draw_pct": "25.0",
    }
    assert classify_draw_system_type(row) == "OTC_OR_REMAINING_TARGET"
    sanitized = sanitize_modeled_probability_fields(dict(row))
    assert sanitized["algorithm_status"] == "EXCLUDED_NOT_PREDICTIVE_DRAW"
    assert sanitized["p_draw"] == ""
    assert sanitized["p_draw_pct"] == ""
