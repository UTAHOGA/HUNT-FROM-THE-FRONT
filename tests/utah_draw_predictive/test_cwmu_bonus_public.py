from engine.utah_draw_predictive.special_bonus import build_phase6_bonus_special_predictions


def test_public_cwmu_rows_can_be_modeled_bonus() -> None:
    truth_rows = [
        {
            "hunt_code": "DB1258",
            "hunt_name": "Little Red Creek CWMU",
            "species": "Deer",
            "sex_type": "Buck",
            "hunt_type": "CWMU",
            "hunt_class": "CWMU",
            "weapon": "Any Legal Weapon",
            "year": "2023",
            "draw_pool": "standard",
            "residency": "Resident",
            "points": "0",
            "eligible_applicants": "12",
            "bonus_permits": "0",
            "regular_permits": "1",
            "total_permits": "1",
        },
        {
            "hunt_code": "DB1258",
            "hunt_name": "Little Red Creek CWMU",
            "species": "Deer",
            "sex_type": "Buck",
            "hunt_type": "CWMU",
            "hunt_class": "CWMU",
            "weapon": "Any Legal Weapon",
            "year": "2025",
            "draw_pool": "standard",
            "residency": "Resident",
            "points": "0",
            "eligible_applicants": "10",
            "bonus_permits": "0",
            "regular_permits": "1",
            "total_permits": "1",
        },
        {
            "hunt_code": "DB1258",
            "hunt_name": "Little Red Creek CWMU",
            "species": "Deer",
            "sex_type": "Buck",
            "hunt_type": "CWMU",
            "hunt_class": "CWMU",
            "weapon": "Any Legal Weapon",
            "year": "2025",
            "draw_pool": "standard",
            "residency": "Resident",
            "points": "1",
            "eligible_applicants": "4",
            "bonus_permits": "1",
            "regular_permits": "0",
            "total_permits": "1",
        },
    ]
    db_rows = [
        {
            "hunt_code": "DB1258",
            "hunt_name": "Little Red Creek CWMU",
            "species": "Deer",
            "sex_type": "Buck",
            "hunt_type": "CWMU",
            "weapon": "Any Legal Weapon",
            "permits_2026_total": "2",
            "permits_2026_res": "2",
            "permits_2026_nr": "0",
        }
    ]

    rows, report = build_phase6_bonus_special_predictions(
        truth_rows=truth_rows,
        db_rows=db_rows,
        forecast_year=2026,
        history_years=[2021, 2022, 2023, 2024, 2025],
    )

    modeled = [row for row in rows if row["draw_system_type"] == "BONUS_CWMU_BIG_GAME" and row["bonus_special_valid"] == "TRUE"]
    assert modeled
    assert report["cwmu_public_modeled_row_count"] == len(modeled)
    assert all(row["p_bonus_pool"] != "" for row in modeled)
    assert all(row["p_draw"] != "" for row in modeled)
    assert all(row["p_preference_draw"] == "" for row in modeled)
