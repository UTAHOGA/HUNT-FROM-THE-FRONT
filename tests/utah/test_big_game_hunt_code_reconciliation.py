from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "processed_data/2026_big_game_hunt_code_reconciliation_summary.json"
RECONCILIATION = ROOT / "processed_data/2026_big_game_hunt_code_reconciliation.csv"


def test_big_game_hunt_codes_reconcile_across_required_surfaces() -> None:
    subprocess.run([sys.executable, "scripts/reconcile-big-game-hunt-codes-2026.py"], cwd=ROOT, check=True)

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "BIG_GAME_HUNT_CODE_RECONCILIATION"
    assert summary["guidebook_hunt_codes"] == 728
    assert summary["codes_present_in_all_required_surfaces"] == 728
    assert summary["required_surface_blocker_count"] == 0
    assert summary["required_missing_by_surface"] == {
        "DATABASE": 0,
        "hunt_master_enriched": 0,
        "hunt_unit_reference_linked": 0,
        "point_ladder_view": 0,
        "draw_reality_engine": 0,
    }
    assert summary["optional_predictive_missing_count"] == 0

    with RECONCILIATION.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 728
    assert {row["required_surface_status"] for row in rows} == {"PASS"}
    assert any(
        row["hunt_code"] == "DB0008" and row["optional_predictive_status"] == "PASS"
        for row in rows
    )
