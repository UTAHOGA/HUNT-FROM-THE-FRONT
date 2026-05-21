import json
from pathlib import Path


def test_phase7_turkey_coverage_report_fields_exist() -> None:
    report_path = Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\draw_system_coverage_report.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    phase7 = report["phase7_turkey"]

    assert "turkey_modeled_bonus_row_count" in phase7
    assert "turkey_in_scope_model_pending_row_count" in phase7
    assert "turkey_excluded_not_predictive_draw_row_count" in phase7
    assert "general_season_turkey_excluded" in phase7
    assert "remaining_turkey_excluded_or_availability_pending" in phase7
