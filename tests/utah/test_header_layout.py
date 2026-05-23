from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HEADER_LAYOUT = ROOT / "header-layout.js"
PAGES = [
    ROOT / "index.html",
    ROOT / "research.html",
    ROOT / "verify.html",
    ROOT / "hard-copy.html",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_shared_header_builds_primary_navigation() -> None:
    text = _text(HEADER_LAYOUT)
    assert "ensurePrimaryHeaderNav" in text
    assert "uoga-primary-nav" in text
    assert "U.O.G.A. HOME" in text
    assert "https://www.uoga.org" in text
    assert "HUNT LIBRARY" in text


def test_center_nav_uses_double_pillow_visual_language() -> None:
    text = _text(HEADER_LAYOUT)
    assert ".uoga-primary-nav::before" in text
    assert "border-radius:999px" in text
    assert "linear-gradient(180deg,#fffdfa" in text
    assert "linear-gradient(180deg, rgba(57,44,34,.96)" in text


def test_nav_items_expand_on_hover() -> None:
    text = _text(HEADER_LAYOUT)
    assert ".uoga-primary-nav a:hover" in text
    assert "scale(1.10)" in text
    assert "translateY(-4px)" in text


def test_active_nav_item_uses_white_text_and_individual_brown_pill() -> None:
    text = _text(HEADER_LAYOUT)
    assert ".uoga-primary-nav a.active" in text
    assert "color:#ffffff" in text
    assert "border:1px solid rgba(240,120,0,.40)" in text
    assert "linear-gradient(180deg, rgba(57,44,34,.92)" in text


def test_pages_use_fresh_header_asset_and_hunt_library_label() -> None:
    for page in PAGES:
        text = _text(page)
        assert "header-layout.js?v=20260523-double-pillow-header-1" in text
        assert "HUNT LIBRARY" in text
        assert "HARD COPIES" not in text
