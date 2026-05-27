from engine.utah_draw_predictive.classifier import classify_draw_system_type, resolve_algorithm_status
from engine.utah_draw_predictive.youth import build_youth_predictions


def test_draw_only_youth_elk_rows_classify_to_specific_family() -> None:
    row = {
        "hunt_code": "EB1007",
        "hunt_name": "Draw-only Youth Any Bull/Hunters Choice Elk",
        "species": "Elk",
        "sex_type": "Bull",
        "hunt_type": "General Season - Any Bull",
        "hunt_class": "Youth",
        "weapon": "Any Legal Weapon",
        "draw_pool": "standard",
        "source_file": "DATABASE.csv",
    }
    assert classify_draw_system_type(row) == "YOUTH_DRAW_ONLY_ELK"


def test_general_season_youth_elk_routes_to_availability_not_youth_draw() -> None:
    row = {
        "hunt_code": "EB1011",
        "hunt_name": "Youth General Season Bull Elk",
        "species": "Elk",
        "sex_type": "Bull",
        "hunt_type": "General Season - Youth",
        "hunt_class": "General Bull",
        "weapon": "Any Legal Weapon",
        "draw_pool": "standard",
        "source_file": "DATABASE.csv",
    }
    draw_system_type = classify_draw_system_type(row)
    assert draw_system_type == "OTC_OR_REMAINING_TARGET"
    assert resolve_algorithm_status(row, draw_system_type) == "EXCLUDED_NOT_PREDICTIVE_DRAW"


def test_youth_general_any_bull_elk_rows_stay_pending_without_fake_odds() -> None:
    db_rows = [
        {
            "hunt_code": "EB1007",
            "hunt_name": "Draw-only Youth Any Bull/Hunters Choice Elk",
            "species": "Elk",
            "sex_type": "Bull",
            "hunt_type": "General Season - Any Bull",
            "hunt_class": "Youth",
            "weapon": "Any Legal Weapon",
            "season": "Sept 12 2026 - Sept 22 2026",
            "permits_2026_total": "750",
        },
        {
            "hunt_code": "EB1011",
            "hunt_name": "Youth General Season Bull Elk",
            "species": "Elk",
            "sex_type": "Bull",
            "hunt_type": "General Season - Youth",
            "hunt_class": "General Bull",
            "weapon": "Any Legal Weapon",
        },
    ]
    rows, _report = build_youth_predictions([], db_rows, 2026, [2025])
    elk_rows = [row for row in rows if row.get("draw_system_type") == "YOUTH_DRAW_ONLY_ELK"]
    assert {row.get("hunt_code") for row in elk_rows} == {"EB1007"}
    assert all(row.get("algorithm_status") == "IN_SCOPE_MODEL_PENDING" for row in elk_rows)
    assert all((row.get("p_draw") or "").strip() == "" for row in elk_rows)
    assert all((row.get("p_draw_pct") or "").strip() == "" for row in elk_rows)
