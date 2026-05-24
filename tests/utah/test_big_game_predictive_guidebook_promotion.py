from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "processed_data/2026_big_game_predictive_v2_guidebook_promotion_summary.json"
DETAIL = ROOT / "processed_data/2026_big_game_predictive_v2_guidebook_promotion.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"


EXPECTED_PROMOTED_CODES = {
    "BI6539",
    "DB0008",
    "DB1109",
    "DB1121",
    "DB1599",
    "DB1600",
    "DB1601",
    "DB1602",
    "DB1603",
    "DB1604",
    "DB1605",
    "DB1606",
    "DB1607",
    "DB1608",
    "DB1609",
    "DB1610",
    "DB1611",
    "DB1612",
    "DB1613",
    "DB1614",
    "DB1615",
    "DB1616",
    "DB1617",
    "DB1618",
    "DB1619",
    "DB1620",
    "DB1621",
    "DB1622",
    "DB1623",
    "DB1624",
    "DB1625",
    "DB1627",
    "DB1628",
    "DB1629",
    "DB1630",
    "DB1631",
    "DB1799",
    "DB1800",
    "DB1801",
    "DB1802",
    "DB1803",
    "DB1804",
    "DB1805",
    "DB1806",
}


def test_guidebook_codes_are_promoted_to_predictive_v2_without_modeling_odds() -> None:
    subprocess.run([sys.executable, "scripts/promote-guidebook-codes-to-predictive-v2-2026.py"], cwd=ROOT, check=True)

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["classification"] == "GUIDEBOOK_TRUTH_REFERENCE_PROMOTION"
    assert summary["promoted_hunt_code_count"] == 44
    assert summary["blocked_hunt_code_count"] == 0
    assert summary["still_missing_hunt_code_count"] == 0
    assert set(summary["promoted_hunt_codes"]) == EXPECTED_PROMOTED_CODES

    with DETAIL.open(newline="", encoding="utf-8-sig") as handle:
        detail_rows = list(csv.DictReader(handle))
    assert len(detail_rows) == 44
    assert {row["promotion_status"] for row in detail_rows} == {"PROMOTED"}

    with PREDICTIVE.open(newline="", encoding="utf-8-sig") as handle:
        predictive_rows = [row for row in csv.DictReader(handle) if row["hunt_code"] in EXPECTED_PROMOTED_CODES]

    assert {row["hunt_code"] for row in predictive_rows} == EXPECTED_PROMOTED_CODES
    assert {row["algorithm_status"] for row in predictive_rows} == {"GUIDEBOOK_TRUTH_REFERENCE"}
    assert {row["probability_model"] for row in predictive_rows} == {"NONE"}
    assert {row["display_odds_text"] for row in predictive_rows} == {"Guidebook reference only; odds not modeled"}
