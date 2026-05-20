from engine.utah_draw_predictive.classifier import classify_draw_system_type, resolve_algorithm_status


def test_bear_classification() -> None:
    row = {"hunt_type": "Limited Entry - Fall", "species": "Black Bear", "sex_type": "Either Sex"}
    assert classify_draw_system_type(row) == "BEAR_DRAW"
    assert resolve_algorithm_status(row) == "IN_SCOPE_MODEL_PENDING"
