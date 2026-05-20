from engine.utah_draw_predictive.classifier import classify_draw_system_type


def test_oil_le_ple_big_game_rows_continue_to_classify_as_bonus() -> None:
    assert classify_draw_system_type({"hunt_type": "Once-in-a-lifetime", "species": "Moose", "sex_type": "Bull"}) == "BONUS_OIL_BIG_GAME"
    assert classify_draw_system_type({"hunt_type": "Limited Entry", "species": "Elk", "sex_type": "Bull"}) == "BONUS_LE_BIG_GAME"
    assert classify_draw_system_type({"hunt_type": "Premium Limited Entry", "species": "Deer", "sex_type": "Buck"}) == "BONUS_PLE_BIG_GAME"


def test_turkey_bear_and_cougar_remain_target_scope() -> None:
    assert classify_draw_system_type({"hunt_type": "Limited Entry", "species": "Turkey", "sex_type": "Bearded"}) == "BONUS_TURKEY"
    assert classify_draw_system_type({"hunt_type": "Limited Entry - Fall", "species": "Black Bear", "sex_type": "Either Sex"}) == "BEAR_DRAW"
    assert classify_draw_system_type({"hunt_type": "Limited Entry", "species": "Cougar", "sex_type": ""}) == "MOUNTAIN_LION_DRAW"


def test_antlerless_moose_and_ewe_bighorn_can_classify_as_bonus() -> None:
    assert classify_draw_system_type({"hunt_type": "Limited Entry", "species": "Moose", "sex_type": "Antlerless"}) == "BONUS_ANTLERLESS_MOOSE"
    assert classify_draw_system_type({"hunt_type": "General Season", "species": "Rocky Mountain Bighorn Sheep", "sex_type": "Ewe"}) == "BONUS_EWE_BIGHORN"


def test_private_lands_only_antlerless_elk_classifies_separately() -> None:
    row = {"hunt_type": "General Season - Private Land Only", "species": "Elk", "sex_type": "Antlerless", "hunt_name": "Private Lands Only Antlerless Elk"}
    assert classify_draw_system_type(row) == "PRIVATE_LANDS_ONLY_ANTLERLESS_ELK"
