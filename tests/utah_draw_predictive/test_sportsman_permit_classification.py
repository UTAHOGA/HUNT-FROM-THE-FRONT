from engine.utah_draw_predictive.classifier import classify_draw_system_type


def test_sportsman_permits_are_not_detected_by_1000_suffix_alone() -> None:
    assert classify_draw_system_type({"hunt_code": "BR1000", "hunt_name": "Black Bear - Statewide Permit", "species": "Black Bear", "hunt_type": "Statewide"}) == "SPORTSMAN_PERMIT"
    assert classify_draw_system_type({"hunt_code": "RS0001", "hunt_name": "Rocky Mountain Bighorn Sheep - Statewide Permit", "species": "Rocky Mountain Bighorn Sheep", "hunt_type": "Statewide"}) == "SPORTSMAN_PERMIT"
    assert classify_draw_system_type({"hunt_code": "DB0007", "hunt_name": "Buck Deer - Statewide Permit", "species": "Deer", "hunt_type": "Statewide"}) == "SPORTSMAN_PERMIT"
    assert classify_draw_system_type({"hunt_code": "TK0001", "hunt_name": "Turkey - Statewide Permit", "species": "Turkey", "hunt_type": "Statewide"}) == "SPORTSMAN_PERMIT"
    assert classify_draw_system_type({"hunt_code": "DB1007", "hunt_name": "Henry Mtns", "species": "Deer", "hunt_type": "Premium Limited Entry"}) != "SPORTSMAN_PERMIT"
