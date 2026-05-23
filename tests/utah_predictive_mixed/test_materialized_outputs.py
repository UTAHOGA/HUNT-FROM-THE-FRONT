from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ML = ROOT / "processed_data" / "ml_draw_predictions_v1.csv"
SUMMARY = ROOT / "processed_data" / "mixed_predictive_engine_2026_summary.json"


def rows() -> list[dict[str, str]]:
    with ML.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_materialized_outputs_have_required_fields_and_no_duplicate_keys() -> None:
    data = rows()
    required = {"p_prior_year_baseline", "p_quota_adjusted", "p_rollover_adjusted", "p_harvest_adjusted", "display_odds_text"}
    assert required.issubset(data[0])
    keys = [(r["hunt_code"], r["residency"], r["points"]) for r in data]
    assert len(keys) == len(set(keys))
    assert json.loads(SUMMARY.read_text(encoding="utf-8"))["duplicate_key_count"] == 0


def test_availability_and_allocation_rows_have_blank_p_draw() -> None:
    for row in rows():
        if row["algorithm_status"] in {"MODELED_AVAILABILITY", "MODELED_ALLOCATION"}:
            assert row["p_draw_mean"] == ""
            assert row["p_draw"] == ""


def test_sportsman_rows_use_sportsman_model_only() -> None:
    sportsman = [row for row in rows() if row["algorithm_status"] == "MODELED_SPORTSMAN_DRAW"]
    assert sportsman
    assert all("SPORTSMAN_SEPARATE_MODEL" in row["reason_codes"] for row in sportsman)


def test_output_display_odds_use_combined_format() -> None:
    modeled = [row for row in rows() if row["p_draw_mean"] and float(row["p_draw_mean"]) > 0]
    assert modeled
    assert all(row["display_odds_text"].startswith("~1 in ") and " or " in row["display_odds_text"] for row in modeled[:100])
