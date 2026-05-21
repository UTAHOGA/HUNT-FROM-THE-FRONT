import csv
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_phase7_turkey_artifacts_are_generated(tmp_path: Path) -> None:
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

    csv_path = tmp_path / "turkey_bonus_predictions_v1.csv"
    json_path = tmp_path / "turkey_bonus_report.json"
    assert csv_path.exists()
    assert json_path.exists()

    rows = _read_csv(csv_path)
    report = json.loads(json_path.read_text(encoding="utf-8"))
    modeled_rows = [row for row in rows if row.get("algorithm_status") == "MODELED_BONUS"]
    pending_rows = [row for row in rows if row.get("algorithm_status") == "IN_SCOPE_MODEL_PENDING"]

    assert rows
    assert report["forecast_year"] == 2026
    assert report["p_preference_draw_non_null_count"] == 0
    assert all(str(row.get("p_preference_draw") or "").strip() == "" for row in modeled_rows)
    assert all(str(row.get("p_bonus_pool") or "").strip() != "" for row in modeled_rows)
    assert all(str(row.get("p_random_pool") or "").strip() != "" for row in modeled_rows)
    assert all(str(row.get("p_draw") or "").strip() != "" for row in modeled_rows)
    assert all(0.0 <= float(row["p_draw"]) <= 1.0 for row in modeled_rows if str(row.get("p_draw") or "").strip())
    assert all(0.0 <= float(row["p_draw_pct"]) <= 100.0 for row in modeled_rows if str(row.get("p_draw_pct") or "").strip())
    assert all(str(row.get("p_draw") or "").strip() == "" for row in pending_rows)
