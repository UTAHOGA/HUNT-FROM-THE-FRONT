from engine.utah_draw_predictive.classifier import classify_draw_system_type
from engine.utah_draw_predictive.youth import build_youth_predictions


def test_youth_rows_do_not_accidentally_classify_as_bonus_or_adult_preference() -> None:
    youth_deer = {
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
    youth_elk = {
        "hunt_code": "EB1011",
        "hunt_name": "Youth General Season Bull Elk",
        "species": "Elk",
        "sex_type": "Bull",
        "hunt_type": "General Season - Youth",
        "hunt_class": "General Bull",
        "weapon": "Any Legal Weapon",
        "source_file": "DATABASE.csv",
    }
    assert classify_draw_system_type(youth_deer) != "PREFERENCE_GENERAL_SEASON_BUCK_DEER"
    assert classify_draw_system_type(youth_elk) not in {"BONUS_OIL_BIG_GAME", "BONUS_LE_BIG_GAME", "BONUS_PLE_BIG_GAME"}
    assert classify_draw_system_type(youth_elk) == "OTC_OR_REMAINING_TARGET"


def test_youth_artifact_rows_do_not_use_bonus_or_preference_fields() -> None:
    rows, _report = build_youth_predictions(
        [],
        [
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
            }
        ],
        2026,
        [2025],
    )
    assert all((row.get("p_bonus_pool") or "").strip() == "" for row in rows)
    assert all((row.get("p_random_pool") or "").strip() == "" for row in rows)
    assert all((row.get("p_preference_draw") or "").strip() == "" for row in rows)
