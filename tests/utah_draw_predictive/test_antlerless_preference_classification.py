from engine.utah_draw_predictive.classifier import classify_draw_system_type


def test_antlerless_preference_classification() -> None:
    assert classify_draw_system_type({"hunt_type": "General Season", "species": "Deer", "sex_type": "Antlerless"}) == "PREFERENCE_ANTLERLESS_DEER"
    assert classify_draw_system_type({"hunt_type": "General Season", "species": "Elk", "sex_type": "Antlerless"}) == "PREFERENCE_ANTLERLESS_ELK"
    assert classify_draw_system_type({"hunt_type": "General Season", "species": "Pronghorn", "sex_type": "Doe"}) == "PREFERENCE_DOE_PRONGHORN"
