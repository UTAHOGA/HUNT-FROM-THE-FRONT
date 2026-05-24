from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "processed_data/2026_big_game_application_guidebook_vs_DATABASE_summary.json"
COMPARE = ROOT / "processed_data/2026_big_game_application_guidebook_vs_DATABASE.csv"
GUIDEBOOK_TABLES = (
    ROOT / "data_truth/regulations_truth/normalized/2026_big_game_application_guidebook_hunt_tables.csv"
)
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"


def _run(script: str) -> None:
    subprocess.run([sys.executable, script], cwd=ROOT, check=True)


def test_big_game_application_guidebook_audit_runs_and_writes_outputs() -> None:
    _run("scripts/audit-big-game-application-guidebook-2026.py")

    assert SUMMARY.exists()
    assert COMPARE.exists()
    assert GUIDEBOOK_TABLES.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "REGULATION_REFERENCE_ONLY"
    assert summary["modeling_guardrail"] == "DO_NOT_USE_AS_DRAW_ODDS_HARVEST_FEATURE_OR_2026_QUOTA_INPUT"
    assert summary["guidebook_unique_hunt_codes"] == 728
    assert summary["matched_database_hunt_codes"] == 728
    assert summary["missing_database_hunt_codes"] == 0
    assert summary["season_review_warnings"] == 0
    assert summary["blockers"] == 0


def test_rs6700_database_season_matches_2026_big_game_application_guidebook() -> None:
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for row in csv.DictReader(handle) if row["hunt_code"] == "RS6700"]

    assert len(rows) == 1
    assert rows[0]["hunt_name"] == "Antelope Island"
    assert rows[0]["species"] == "Rocky Mountain Bighorn Sheep"
    assert rows[0]["season"] == "Nov 09, 2026 - Nov 16, 2026"
