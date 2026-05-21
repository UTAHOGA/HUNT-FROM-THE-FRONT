import json
from pathlib import Path


def test_phase15_youth_coverage_fields_are_present() -> None:
    report = json.loads(
        Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\draw_system_coverage_report.json").read_text(encoding="utf-8")
    )
    section = report["phase15_youth"]

    assert section["youth_general_deer_in_scope"] is True
    assert section["youth_general_any_bull_elk_in_scope"] is True
    assert section["youth_general_deer_modeled"] is False
    assert section["youth_general_deer_still_pending"] is True
    assert section["youth_general_any_bull_elk_still_pending"] is True
    assert section["youth_general_any_bull_elk_active_predictive_row_count"] >= 0
    assert section["youth_rows_with_p_draw_non_null_count"] == 0
    assert section["youth_rows_with_p_bonus_pool_non_null_count"] == 0
    assert section["youth_rows_with_p_random_pool_non_null_count"] == 0
    assert section["youth_rows_with_p_preference_draw_non_null_count"] == 0
