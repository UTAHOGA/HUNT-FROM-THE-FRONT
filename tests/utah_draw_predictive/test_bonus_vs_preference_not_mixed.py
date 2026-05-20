from engine.utah_draw_predictive.classifier import classify_draw_system_type


def test_general_season_buck_deer_does_not_classify_as_bonus() -> None:
    row = {"hunt_type": "General Season", "hunt_class": "General-season Archery Buck Deer", "species": "Deer", "sex_type": "Buck"}
    assert classify_draw_system_type(row) == "PREFERENCE_GENERAL_SEASON_BUCK_DEER"


def test_dedicated_hunter_deer_does_not_classify_as_bonus() -> None:
    row = {"hunt_type": "General Season", "species": "Deer", "sex_type": "Buck", "weapon": "Dedicated Hunter"}
    assert classify_draw_system_type(row) == "PREFERENCE_DEDICATED_HUNTER_DEER"


def test_antlerless_deer_elk_and_doe_pronghorn_do_not_classify_as_bonus() -> None:
    assert classify_draw_system_type({"hunt_type": "General Season", "hunt_class": "General-season Antlerless Deer", "species": "Deer", "sex_type": "Antlerless"}) == "PREFERENCE_ANTLERLESS_DEER"
    assert classify_draw_system_type({"hunt_type": "General Season", "hunt_class": "General-season Antlerless Elk", "species": "Elk", "sex_type": "Antlerless"}) == "PREFERENCE_ANTLERLESS_ELK"
    assert classify_draw_system_type({"hunt_type": "General Season", "hunt_class": "General-season Doe Pronghorn", "species": "Pronghorn", "sex_type": "Doe"}) == "PREFERENCE_DOE_PRONGHORN"
