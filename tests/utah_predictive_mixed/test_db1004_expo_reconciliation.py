from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_db1004_expo_reconciliation_result() -> None:
    summary = json.loads((ROOT / "processed_data" / "mixed_predictive_engine_2026_summary.json").read_text(encoding="utf-8"))
    result = summary["db1004_reconciliation"]
    assert result == {
        "public_draw_2025_permits": "80",
        "expo_permits": "3",
        "all_class_total": "83",
        "conservation_used": False,
        "sample_display_odds_text": result["sample_display_odds_text"],
    }
