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
    assert classify_draw_system_type(row) == "YOUTH_GENERAL_DEER"
