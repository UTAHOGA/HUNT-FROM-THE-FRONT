from engine.utah_draw_predictive.preference_antlerless import STRATEGY_SPECS


def test_antlerless_preference_strategies_are_classified_not_modeled() -> None:
    mapped = {spec.draw_system_type: spec for spec in STRATEGY_SPECS}
    for draw_system_type in (
        "PREFERENCE_ANTLERLESS_DEER",
        "PREFERENCE_ANTLERLESS_ELK",
        "PREFERENCE_DOE_PRONGHORN",
    ):
        assert mapped[draw_system_type].algorithm_status == "IN_SCOPE_MODEL_PENDING"
        assert "bonus model" in mapped[draw_system_type].reason
