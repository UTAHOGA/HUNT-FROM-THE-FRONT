from __future__ import annotations

import csv
from pathlib import Path


def test_max_pool_not_automatic_100():
    text = Path("hunt-research.js").read_text(encoding="utf-8")
    assert "if (row.status === 'MAX POOL') return 100;" not in text
    assert "if (!hasModeledFields && row.status === 'MAX POOL') return { value: '100%', source: 'guaranteed' };" not in text
    assert "badge: 'Guaranteed'" in text


def test_frontend_uses_modeled_probability_before_legacy_max_pool():
    text = Path("hunt-research.js").read_text(encoding="utf-8")
    start = text.index("function getDisplayedOdds(row)")
    end = text.index("function isPreferenceAntlerless(meta)")
    block = text[start:end]
    assert "p_draw_pct" in block
    assert "p_draw" in block
    assert "p_bonus_pool_pct" in block
    assert "p_random_pool_pct" in block
    assert block.index("p_draw_pct") < block.index("odds_2026_projected")
    assert block.index("p_draw") < block.index("odds_2026_projected")
    assert "row.status === 'MAX POOL'" not in block


def test_fixture_row_with_max_pool_and_modeled_probability_exists():
    rows = list(csv.DictReader(Path("data/utah/fixtures/draw_reality_engine.csv").open(encoding="utf-8")))
    row = next(r for r in rows if r["status"] == "MAX POOL")
    assert row["p_draw_mean"] == "0.420"
    assert row["guaranteed_probability"] == "0.000"
    assert row["display_odds_pct"] == "42.000"

    # Required contract: MAX POOL does not force 100% when modeled values exist.
    display_pct = float(row["display_odds_pct"])
    guaranteed_probability = float(row["guaranteed_probability"])
    p_draw_mean = float(row["p_draw_mean"])
    assert display_pct == 42.0
    assert round(p_draw_mean * 100, 3) == 42.0
    assert guaranteed_probability < 0.999


def test_max_pool_fixture_row_is_not_guaranteed_badge():
    rows = list(csv.DictReader(Path("data/utah/fixtures/draw_reality_engine.csv").open(encoding="utf-8")))
    row = next(r for r in rows if r["status"] == "MAX POOL")
    guaranteed_probability = float(row["guaranteed_probability"])
    p_draw_mean = float(row["p_draw_mean"])

    if guaranteed_probability >= 0.999:
        badge = "Guaranteed"
    elif p_draw_mean >= 0.90:
        badge = "Very likely"
    elif p_draw_mean >= 0.25:
        badge = "On the Line"
    elif p_draw_mean > 0:
        badge = "Random / Long-shot Chance"
    else:
        badge = "Not Catchable Right Now"

    assert badge != "Guaranteed"
    assert badge == "On the Line"

