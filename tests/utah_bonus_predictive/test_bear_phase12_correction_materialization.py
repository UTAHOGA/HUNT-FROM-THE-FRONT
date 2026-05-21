import csv
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_bear_phase12_correction_writes_source_audit_and_bonus_pursuit_rows(tmp_path: Path) -> None:
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

    bear_rows = _read_csv(tmp_path / "bear_predictions_v1.csv")
    audit_rows = _read_csv(tmp_path / "bear_draw_odds_source_audit.csv")
    audit_report = json.loads((tmp_path / "bear_draw_odds_source_audit.json").read_text(encoding="utf-8"))

    assert bear_rows
    assert audit_rows
    assert audit_report["bear_pursuit_hunt_codes_found_in_official_draw_odds_pdf"] >= 9
    for hunt_code in {"BR1008", "BR1009", "BR1011"}:
        modeled = [row for row in bear_rows if row.get("hunt_code") == hunt_code and row.get("algorithm_status") == "MODELED_BONUS"]
        assert modeled
        assert all((row.get("p_bonus_pool") or "").strip() != "" for row in modeled)
        assert all((row.get("p_random_pool") or "").strip() != "" for row in modeled)
