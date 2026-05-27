from engine.utah_draw_predictive.classifier import classify_draw_system_type


def test_youth_general_deer_rows_classify_separately_from_adult_general_deer() -> None:
    row = {
        "hunt_code": "DB1501",
        "hunt_name": "Box Elder",
        "species": "Deer",
        "sex_type": "Buck",
        "hunt_type": "General Season",
        "hunt_class": "General-season Archery Buck Deer",
        "weapon": "Archery",
        "draw_pool": "youth",
        "source_file": "2025 Youth G.S. Deer Draw Results.pdf",
    }
    assert classify_draw_system_type(row) == "YOUTH_GENERAL_DEER_RESERVE"


def test_youth_antlerless_or_doe_rows_classify_to_reserve_family() -> None:
    antlerless_elk = {
        "hunt_code": "EA1239",
        "hunt_name": "Nine Mile, Range Creek",
        "species": "Elk",
        "sex_type": "Antlerless",
        "hunt_type": "General Season",
        "hunt_class": "Antlerless",
        "weapon": "Any Legal Weapon",
        "draw_pool": "youth",
        "source_file": "2025 Youth Antlerless Draw.pdf",
    }
    doe_pronghorn = {
        "hunt_code": "PD1008",
        "hunt_name": "Southwest Desert, Milford Flat",
        "species": "Pronghorn",
        "sex_type": "Doe",
        "hunt_type": "Antlerless",
        "hunt_class": "Doe",
        "weapon": "Any Legal Weapon",
        "draw_pool": "youth",
        "source_file": "2025 Youth Antlerless Draw.pdf",
    }
    assert classify_draw_system_type(antlerless_elk) == "YOUTH_ANTLERLESS_OR_DOE_RESERVE"
    assert classify_draw_system_type(doe_pronghorn) == "YOUTH_ANTLERLESS_OR_DOE_RESERVE"
