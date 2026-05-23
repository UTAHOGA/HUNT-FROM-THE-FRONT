from __future__ import annotations

import csv
from pathlib import Path


FRONTEND_PATH = Path("hunt-research.js")
RESEARCH_HTML_PATH = Path("research.html")
FIXTURE_PATH = Path("data/utah/fixtures/draw_reality_engine.csv")


def _frontend_text() -> str:
    return FRONTEND_PATH.read_text(encoding="utf-8")


def _block(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def _fixture_max_pool_row() -> dict[str, str]:
    rows = list(csv.DictReader(FIXTURE_PATH.open(encoding="utf-8")))
    return next(r for r in rows if r["status"] == "MAX POOL")


def _select_draw_odds_percent(row: dict[str, str]) -> float | None:
    for key in (
        "display_odds_pct",
        "p_draw_mean",
        "odds_2026_projected",
        "max_pool_projection_2026",
        "random_draw_odds_2026",
        "random_draw_projection_2026",
    ):
        value = row.get(key, "")
        if value in ("", None):
            continue
        parsed = float(value)
        if key == "p_draw_mean":
            return parsed * 100
        return parsed
    return None


def _format_combined_odds(percent_value: float | None) -> str:
    if percent_value is None:
        return "Not available"
    if percent_value <= 0:
        return "No modeled chance"

    capped = min(100.0, max(0.0, percent_value))
    percent_text = f"{int(capped)}%" if float(capped).is_integer() else f"{float(f'{capped:.1f}')}%"

    if capped >= 99.9:
        return f"~1 in 1 or {percent_text}"

    denominator = 100 / capped
    denominator_text = str(float(f"{denominator:.1f}")).rstrip("0").rstrip(".") if denominator < 10 else str(round(denominator))
    return f"~1 in {denominator_text} or {percent_text}"


def _verdict_badge_from_selected_odds(row: dict[str, str]) -> str:
    guaranteed_probability = float(row["guaranteed_probability"])
    selected_percent = _select_draw_odds_percent(row)
    if guaranteed_probability >= 0.999:
        return "Guaranteed"
    if selected_percent is None:
        return "Random Chance Only"
    if selected_percent >= 99.9:
        return "Guaranteed"
    if selected_percent >= 90:
        return "Very likely"
    if selected_percent >= 25:
        return "On the Line"
    if selected_percent > 0:
        return "Random / Long-shot Chance"
    return "Not Catchable Right Now"


def _outlook_signal_from_selected_odds(row: dict[str, str]) -> str:
    guaranteed_probability = float(row["guaranteed_probability"])
    selected_percent = _select_draw_odds_percent(row)
    if guaranteed_probability >= 0.999:
        return "green"
    if selected_percent is None:
        return "red"
    if selected_percent >= 99.9:
        return "green"
    if selected_percent >= 25:
        return "yellow"
    return "red"


def test_max_pool_not_automatic_100():
    text = _frontend_text()
    assert "if (row.status === 'MAX POOL') return 100;" not in text
    assert "if (!hasModeledFields && row.status === 'MAX POOL') return { value: '100%', source: 'guaranteed' };" not in text


def test_frontend_uses_modeled_probability_before_legacy_max_pool():
    text = _frontend_text()
    block = _block(text, "function selectDrawOddsPercent(row)", "function getDisplayedOdds(row)")
    assert "display_odds_pct" in block
    assert "p_draw_mean" in block
    assert "odds_2026_projected" in block
    assert "max_pool_projection_2026" in block
    assert "random_draw_odds_2026" in block
    assert "random_draw_projection_2026" in block
    assert block.index("display_odds_pct") < block.index("p_draw_mean")
    assert block.index("p_draw_mean") < block.index("odds_2026_projected")
    assert "row.status === 'MAX POOL'" not in block


def test_frontend_uses_engine_group_fallback_for_non_point_families():
    text = _frontend_text()
    assert "function getEngineGroupFallbackRow(" in text
    assert "const engineGroupFallbackRow = getEngineGroupFallbackRow(filters.huntCode, filters.residency, filters.drawPool);" in text
    assert "const summaryRow = engineRow || engineGroupFallbackRow || ladderPointRow || null;" in text


def test_fixture_row_with_max_pool_and_modeled_probability_exists():
    row = _fixture_max_pool_row()
    assert row["p_draw_mean"] == "0.420"
    assert row["guaranteed_probability"] == "0.000"
    assert row["display_odds_pct"] == "42.000"
    assert float(row["display_odds_pct"]) == 42.0
    assert round(float(row["p_draw_mean"]) * 100, 3) == 42.0
    assert float(row["guaranteed_probability"]) < 0.999


def test_max_pool_fixture_row_is_not_guaranteed_badge():
    row = _fixture_max_pool_row()
    assert _verdict_badge_from_selected_odds(row) != "Guaranteed"
    assert _verdict_badge_from_selected_odds(row) == "On the Line"


def test_format_odds_combined_guaranteed():
    assert _format_combined_odds(100) == "~1 in 1 or 100%"


def test_format_odds_combined_50_percent():
    assert _format_combined_odds(50) == "~1 in 2 or 50%"


def test_format_odds_combined_42_percent():
    assert _format_combined_odds(42) == "~1 in 2.4 or 42%"


def test_format_odds_combined_25_percent():
    assert _format_combined_odds(25) == "~1 in 4 or 25%"


def test_format_odds_combined_10_percent():
    assert _format_combined_odds(10) == "~1 in 10 or 10%"


def test_format_odds_combined_one_percent():
    assert _format_combined_odds(1) == "~1 in 100 or 1%"


def test_format_odds_combined_zero_percent():
    assert _format_combined_odds(0) == "No modeled chance"


def test_format_odds_combined_missing():
    assert _format_combined_odds(None) == "Not available"


def test_modeled_max_pool_42_percent_displays_one_in_2_4_or_42_percent():
    row = _fixture_max_pool_row()
    assert _format_combined_odds(_select_draw_odds_percent(row)) == "~1 in 2.4 or 42%"


def test_max_pool_status_does_not_display_one_in_1_or_100_without_numeric_guarantee():
    row = _fixture_max_pool_row()
    assert _format_combined_odds(_select_draw_odds_percent(row)) != "~1 in 1 or 100%"


def test_no_percent_only_primary_odds_display():
    text = _frontend_text()
    block = _block(text, "function getPrimaryOddsLabel(meta, row, displayedOdds)", "function getOutlookSignal(meta, row)")
    assert "displayedOdds.value" in block
    assert "formatProbability(" not in block
    assert "summaryOdds.textContent = getPrimaryOddsLabel(meta, row, displayedOdds);" in text


def test_ladder_odds_use_combined_format():
    text = _frontend_text()
    block = _block(text, "function renderLadder(meta, huntCode, residency, points, drawPool)", "function renderEmpty(filters, coverageMessage)")
    assert "formatOddsAsOneInOrPercent(rawPrimary)" in block
    assert "formatOddsAsOneInOrPercent(firstAvailable(row, ['random_draw_projection_2026', 'random_draw_odds_2026', 'odds_2026_projected']))" in block
    assert "formatProbability(rawPrimary)" not in block


def test_source_snapshot_odds_use_combined_format():
    text = _frontend_text()
    block = _block(text, "function buildSourceBoxes(meta, row, referenceRow)", "function openSourceModal(meta, row, referenceRow, residency)")
    assert "formatOddsAsOneInOrPercent(row?.odds_2025_actual)" in block
    assert "['2026 Draw Odds', getDisplayedOdds(row).value]" in block


def test_no_status_max_pool_return_100_shortcut():
    text = _frontend_text()
    assert "row.status === 'MAX POOL'" not in _block(text, "function getDisplayedOdds(row)", "function isPreferenceAntlerless(meta)")


def test_max_pool_status_does_not_force_guaranteed_badge():
    text = _frontend_text()
    block = _block(text, "function getVerdictState(meta, row, filters, coverageMessage)", "function renderVerdict(meta, row, filters, coverageMessage)")
    assert "row.status === 'MAX POOL'" not in block
    assert _verdict_badge_from_selected_odds(_fixture_max_pool_row()) != "Guaranteed"


def test_max_pool_status_does_not_force_green_light():
    text = _frontend_text()
    block = _block(text, "function getOutlookSignal(meta, row)", "function renderOutlookLight(signal)")
    assert "row.status === 'MAX POOL'" not in block
    assert _outlook_signal_from_selected_odds(_fixture_max_pool_row()) != "green"
    assert _outlook_signal_from_selected_odds(_fixture_max_pool_row()) == "yellow"


def test_research_page_green_legend_no_longer_claims_max_pool_guarantee():
    text = RESEARCH_HTML_PATH.read_text(encoding="utf-8")
    assert "Green:</strong> Guaranteed draw." not in text
    assert "Green:</strong> The selected draw-odds field is effectively guaranteed." in text
