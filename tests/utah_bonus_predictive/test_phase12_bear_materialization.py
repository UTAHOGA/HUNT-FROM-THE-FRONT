import csv
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_phase12_bear_artifacts_are_generated(tmp_path: Path) -> None:
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

    csv_path = tmp_path / "bear_predictions_v1.csv"
    json_path = tmp_path / "bear_report.json"
    assert csv_path.exists()
    assert json_path.exists()

    rows = _read_csv(csv_path)
    report = json.loads(json_path.read_text(encoding="utf-8"))
    ho_rows = [row for row in rows if row.get("bear_draw_subtype") == "HARVEST_OBJECTIVE_AVAILABILITY"]
    pursuit_rows = [row for row in rows if row.get("bear_draw_subtype") == "UNLIMITED_PURSUIT_PERMIT"]
    modeled_rows = [row for row in rows if row.get("algorithm_status") == "MODELED_BONUS"]

    assert rows
    assert report["forecast_year"] == 2026
    assert report["harvest_objective_row_count"] == len(ho_rows)
    assert report["unlimited_pursuit_permit_row_count"] == len(pursuit_rows)
    assert report["harvest_objective_p_draw_non_null_count"] == 0
    assert report["unlimited_pursuit_permit_p_draw_non_null_count"] == 0
    assert report["p_preference_draw_non_null_count"] == 0
    assert all((row.get("p_preference_draw") or "").strip() == "" for row in rows)
    assert all((row.get("p_draw") or "").strip() == "" for row in ho_rows)
    assert all((row.get("p_draw") or "").strip() == "" for row in pursuit_rows)
    assert all((row.get("p_bonus_pool") or "").strip() != "" for row in modeled_rows)
