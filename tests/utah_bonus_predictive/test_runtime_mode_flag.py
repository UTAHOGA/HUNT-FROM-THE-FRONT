from pathlib import Path


def test_runtime_mode_flag_and_sources_exist() -> None:
    text = Path("config.js").read_text(encoding="utf-8")
    assert "USE_PREDICTIVE_DRAW_ENGINE" in text
    assert "draw_reality_engine_v2.csv" in text
    assert "draw_reality_engine_predictive_v2.csv" in text
    assert "HUNT_RESEARCH_ENGINE_MODE" in text


def test_hunt_research_uses_engine_mode_from_config() -> None:
    text = Path("hunt-research.js").read_text(encoding="utf-8")
    assert "HUNT_RESEARCH_ENGINE_MODE" in text
    assert "engineMode" in text
