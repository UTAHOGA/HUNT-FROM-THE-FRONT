import csv
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _nonnull(rows: list[dict[str, str]], column: str) -> int:
    return sum(1 for row in rows if str(row.get(column) or "").strip() != "")


def test_formal_cli_generates_populated_artifacts(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.utah_bonus_predictive.materialize",
            "--output-dir",
            str(tmp_path),
            "--forecast-year",
            "2026",
            "--history-years",
            "2021,2022,2023,2024,2025",
            "--skip-upstream",
        ],
        cwd=REPO,
        check=True,
    )

    ml_path = tmp_path / "ml_draw_predictions_v1.csv"
    bt_path = tmp_path / "backtest_utah_bonus_draw.csv"
    successor_path = tmp_path / "draw_reality_engine_predictive_v2.csv"
    runtime_truth_path = tmp_path / "draw_reality_engine_v2.csv"
    report_path = tmp_path / "ml_draw_predictions_v1_report.json"
    coverage_json_path = tmp_path / "predictive_coverage_report.json"
    coverage_csv_path = tmp_path / "predictive_coverage_report.csv"
    dedicated_hunter_csv_path = tmp_path / "dedicated_hunter_predictions_v1.csv"
    dedicated_hunter_report_path = tmp_path / "dedicated_hunter_report.json"
    phase4_inventory_csv_path = tmp_path / "phase4_antlerless_validation_inventory.csv"
    phase4_inventory_json_path = tmp_path / "phase4_antlerless_validation_inventory.json"
    phase6_csv_path = tmp_path / "phase6_bonus_special_predictions_v1.csv"
    phase6_report_path = tmp_path / "phase6_bonus_special_report.json"
    manifest_path = tmp_path / "utah_bonus_predictive_manifest.json"

    assert ml_path.exists()
    assert bt_path.exists()
    assert successor_path.exists()
    assert runtime_truth_path.exists()
    assert report_path.exists()
    assert coverage_json_path.exists()
    assert coverage_csv_path.exists()
    assert dedicated_hunter_csv_path.exists()
    assert dedicated_hunter_report_path.exists()
    assert phase4_inventory_csv_path.exists()
    assert phase4_inventory_json_path.exists()
    assert phase6_csv_path.exists()
    assert phase6_report_path.exists()
    assert manifest_path.exists()

    ml_rows = _read_csv(ml_path)
    bt_rows = _read_csv(bt_path)
    successor_rows = _read_csv(successor_path)
    dedicated_hunter_rows = _read_csv(dedicated_hunter_csv_path)
    phase6_rows = _read_csv(phase6_csv_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    coverage = json.loads(coverage_json_path.read_text(encoding="utf-8"))
    dedicated_hunter_report = json.loads(dedicated_hunter_report_path.read_text(encoding="utf-8"))
    phase6_report = json.loads(phase6_report_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert ml_rows
    assert bt_rows
    assert successor_rows
    assert report["forecast_year"] == 2026
    assert report["source_years"] == "2021-2025"
    assert coverage["total_forecast_hunt_codes"] == len({row["hunt_code"] for row in ml_rows})
    assert "count_excluded_missing_model_input_or_not_in_predictive_draft" in coverage
    assert "active_eligible_codes_missing_from_forecast" in coverage
    assert dedicated_hunter_report["exists"] is True
    assert dedicated_hunter_report["total_rows"] == len(dedicated_hunter_rows)
    assert phase6_report["forecast_year"] == 2026
    assert phase6_report["total_phase6_rows"] == len(phase6_rows)
    assert manifest["forecast_year"] == 2026
    assert manifest["calibration_metric_non_null_count"] == len(bt_rows)

    modeled_bonus_rows = [row for row in ml_rows if row.get("algorithm_status") == "MODELED_BONUS"]
    modeled_preference_rows = [row for row in ml_rows if row.get("algorithm_status") == "MODELED_PREFERENCE"]
    pending_rows = [row for row in ml_rows if row.get("algorithm_status") == "IN_SCOPE_MODEL_PENDING"]
    dedicated_hunter_modeled_rows = [row for row in dedicated_hunter_rows if row.get("algorithm_status") == "MODELED_PREFERENCE"]
    assert modeled_bonus_rows
    assert _nonnull(modeled_bonus_rows, "p_draw") == len(modeled_bonus_rows)
    assert _nonnull(modeled_bonus_rows, "p_draw_pct") == len(modeled_bonus_rows)
    assert modeled_preference_rows
    assert _nonnull(modeled_preference_rows, "p_draw") == len(modeled_preference_rows)
    assert _nonnull(modeled_preference_rows, "p_draw_pct") == len(modeled_preference_rows)
    assert all(str(row.get("p_draw") or "").strip() == "" for row in pending_rows)
    assert all(str(row.get("p_draw_pct") or "").strip() == "" for row in pending_rows)
    assert _nonnull(dedicated_hunter_modeled_rows, "p_preference_draw") == len(dedicated_hunter_modeled_rows)
    assert all((row.get("p_preference_draw") or "") == (row.get("p_draw") or "") for row in dedicated_hunter_modeled_rows)
    assert _nonnull(dedicated_hunter_rows, "p_bonus_pool") == 0
    assert _nonnull(dedicated_hunter_rows, "p_random_pool") == 0
    assert _nonnull(ml_rows, "source_years_used") == len(ml_rows)
    assert _nonnull(bt_rows, "calibration_error_by_probability_bucket") == len(bt_rows)

    keys = [(row["hunt_code"], row["residency"], row["points"]) for row in successor_rows]
    assert len(keys) == len(set(keys))


def test_formal_cli_source_year_traceability_fields(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.utah_bonus_predictive.materialize",
            "--output-dir",
            str(tmp_path),
            "--forecast-year",
            "2026",
            "--history-years",
            "2021,2022,2023,2024,2025",
            "--skip-upstream",
        ],
        cwd=REPO,
        check=True,
    )
    rows = _read_csv(tmp_path / "ml_draw_predictions_v1.csv")
    assert rows
    assert all(str(row.get("source_years_used") or "").strip() for row in rows)
    assert all(str(row.get("source_year_count") or "").strip() for row in rows)
    assert all(str(row.get("earliest_source_year") or "").strip() for row in rows)
    assert all(str(row.get("latest_source_year") or "").strip() for row in rows)
    assert any(row["source_years_used"] == "2021,2022,2023,2024,2025" for row in rows)
