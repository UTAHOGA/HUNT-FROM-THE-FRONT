import csv
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_private_lands_antlerless_elk_allocation_artifacts_are_generated_with_closeout_fields(tmp_path: Path) -> None:
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

    csv_path = tmp_path / "private_lands_antlerless_elk_allocations_v1.csv"
    json_path = tmp_path / "private_lands_antlerless_elk_report.json"
    assert csv_path.exists()
    assert json_path.exists()

    rows = _read_csv(csv_path)
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert rows
    assert report["forecast_year"] == 2026
    assert report["active_predictive_row_count"] == len(rows)
    assert report["modeled_allocation_row_count"] == len(rows)
    assert report["pending_allocation_row_count"] == 0
    assert report["excluded_row_count"] == 0
    assert report["permits_allotted_non_null_count"] == len(rows)
    assert report["permits_remaining_non_null_count"] == 0
    assert report["p_availability_non_null_count"] == 0
    assert report["availability_pct_non_null_count"] == 0
    assert report["sellout_risk_non_null_count"] == 0
    assert report["p_draw_non_null_count"] == 0
    assert report["p_draw_pct_non_null_count"] == 0
    assert report["p_preference_draw_non_null_count"] == 0
    assert report["p_bonus_pool_non_null_count"] == 0
    assert report["p_random_pool_non_null_count"] == 0
    assert report["duplicate_key_count"] == 0
