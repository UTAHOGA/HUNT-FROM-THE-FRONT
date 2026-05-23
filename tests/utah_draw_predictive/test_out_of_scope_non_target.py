from engine.utah_draw_predictive.classifier import (
    classify_draw_system_type,
    sanitize_modeled_probability_fields,
)


def test_non_target_species_classify_as_out_of_scope() -> None:
    assert classify_draw_system_type({"species": "Swan", "hunt_type": "Limited Entry"}) == "OUT_OF_SCOPE_NON_TARGET"
    assert classify_draw_system_type({"species": "Sandhill Crane", "hunt_type": "Limited Entry"}) == "OUT_OF_SCOPE_NON_TARGET"
    assert classify_draw_system_type({"species": "Greater Sage Grouse", "hunt_type": "Limited Entry"}) == "OUT_OF_SCOPE_NON_TARGET"
    assert classify_draw_system_type({"species": "Waterfowl", "hunt_type": "General Season"}) == "OUT_OF_SCOPE_NON_TARGET"
    assert classify_draw_system_type({"species": "Small Game", "hunt_type": "General Season"}) == "OUT_OF_SCOPE_NON_TARGET"
    assert classify_draw_system_type({"species": "Fishing", "hunt_type": "General Season"}) == "OUT_OF_SCOPE_NON_TARGET"
    assert classify_draw_system_type({"species": "Upland Game", "hunt_name": "Sharp-tailed Grouse"}) == "OUT_OF_SCOPE_NON_TARGET"


def test_target_elk_row_with_grouse_creek_name_is_not_out_of_scope() -> None:
    row = {
        "hunt_code": "EB3147",
        "hunt_name": "Limited-entry Alw (rifle) Bull Elk - Early - Box Elder, Grouse Creek - Any Legal Weapon",
        "hunt_type": "Limited Entry",
    }
    assert classify_draw_system_type(row) == "BONUS_LE_BIG_GAME"


def test_out_of_scope_rows_do_not_receive_modeled_odds() -> None:
    row = sanitize_modeled_probability_fields(
        {
            "species": "Swan",
            "hunt_type": "Limited Entry",
            "source_dataset": "predictive",
            "p_draw": "0.750000",
            "p_draw_pct": "75.000",
            "p_bonus_pool": "0.500000",
            "p_random_pool": "0.250000",
        }
    )
    assert row["algorithm_status"] == "OUT_OF_SCOPE_NON_TARGET"
    assert row["p_draw"] == ""
    assert row["p_draw_pct"] == ""
