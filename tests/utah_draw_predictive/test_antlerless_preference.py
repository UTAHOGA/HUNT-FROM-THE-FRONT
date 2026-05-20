from engine.utah_draw_predictive.preference_antlerless import (
    MODEL_STRATEGY_NAME,
    STRATEGY_SPECS,
    build_preference_antlerless_predictions,
    is_modeled_antlerless_row,
)


def test_antlerless_preference_strategies_are_promoted_to_modeled_preference() -> None:
    mapped = {spec.draw_system_type: spec for spec in STRATEGY_SPECS}
    assert mapped["PREFERENCE_ANTLERLESS_DEER"].algorithm_status == "MODELED_PREFERENCE"
    assert mapped["PREFERENCE_ANTLERLESS_ELK"].algorithm_status == "MODELED_PREFERENCE"
    assert mapped["PREFERENCE_DOE_PRONGHORN"].algorithm_status == "MODELED_PREFERENCE"
    assert "preference-point model" in mapped["PREFERENCE_ANTLERLESS_DEER"].reason


def test_build_preference_antlerless_predictions_returns_modeled_rows() -> None:
    truth_rows = [
        {
            "hunt_code": "EA1001",
            "hunt_name": "Central Mtns",
            "species": "Elk",
            "sex_type": "Antlerless",
            "hunt_type": "General Season",
            "hunt_class": "Public",
            "weapon": "Any Legal Weapon",
            "year": "2023",
            "draw_pool": "standard",
            "residency": "Resident",
            "points": "0",
            "eligible_applicants": "40",
            "total_permits": "30",
        },
        {
            "hunt_code": "EA1001",
            "hunt_name": "Central Mtns",
            "species": "Elk",
            "sex_type": "Antlerless",
            "hunt_type": "General Season",
            "hunt_class": "Public",
            "weapon": "Any Legal Weapon",
            "year": "2023",
            "draw_pool": "standard",
            "residency": "Resident",
            "points": "1",
            "eligible_applicants": "8",
            "total_permits": "7",
        },
        {
            "hunt_code": "EA1001",
            "hunt_name": "Central Mtns",
            "species": "Elk",
            "sex_type": "Antlerless",
            "hunt_type": "General Season",
            "hunt_class": "Public",
            "weapon": "Any Legal Weapon",
            "year": "2025",
            "draw_pool": "standard",
            "residency": "Resident",
            "points": "0",
            "eligible_applicants": "36",
            "total_permits": "24",
        },
        {
            "hunt_code": "EA1001",
            "hunt_name": "Central Mtns",
            "species": "Elk",
            "sex_type": "Antlerless",
            "hunt_type": "General Season",
            "hunt_class": "Public",
            "weapon": "Any Legal Weapon",
            "year": "2025",
            "draw_pool": "standard",
            "residency": "Resident",
            "points": "1",
            "eligible_applicants": "11",
            "total_permits": "8",
        },
    ]
    db_rows = [
        {
            "hunt_code": "EA1001",
            "hunt_name": "Central Mtns",
            "species": "Elk",
            "sex_type": "Antlerless",
            "hunt_type": "General Season",
            "weapon": "Any Legal Weapon",
            "permits_2026_total": "40",
        }
    ]

    rows = build_preference_antlerless_predictions(
        truth_rows=truth_rows,
        db_rows=db_rows,
        forecast_year=2026,
        history_years=[2021, 2022, 2023, 2024, 2025],
    )

    assert rows
    assert all(row["model_strategy"] == MODEL_STRATEGY_NAME for row in rows)
    assert all(row["preference_model_valid"] == "TRUE" for row in rows)
    assert all(is_modeled_antlerless_row(row) for row in rows)
    assert all(row["draw_system_type"] == "PREFERENCE_ANTLERLESS_ELK" for row in rows)
    assert any(float(row["p_draw"]) > 0.0 for row in rows)
