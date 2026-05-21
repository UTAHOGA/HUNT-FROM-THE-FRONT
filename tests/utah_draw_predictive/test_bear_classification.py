from engine.utah_draw_predictive.classifier import classify_draw_system_type, resolve_algorithm_status


def test_bear_classification() -> None:
    row = {"hunt_type": "Limited Entry - Fall", "species": "Black Bear", "sex_type": "Either Sex"}
    assert classify_draw_system_type(row) == "BEAR_DRAW"
    assert resolve_algorithm_status(row) == "IN_SCOPE_MODEL_PENDING"


def test_restricted_pursuit_black_bear_stays_in_bear_family() -> None:
    row = {"hunt_type": "Restricted Pursuit - Summer", "species": "Black Bear", "weapon": "Pursuit Only"}
    assert classify_draw_system_type(row) == "BEAR_DRAW"
    assert resolve_algorithm_status(row) != "MODELED_BONUS"


def test_bear_name_in_non_bear_hunt_does_not_false_positive() -> None:
    row = {"hunt_code": "DB1206", "hunt_name": "Bear Mountain CWMU", "species": "Deer", "sex_type": "Buck", "hunt_type": "CWMU", "hunt_class": "CWMU"}
    assert classify_draw_system_type(row) == "BONUS_CWMU_BIG_GAME"
