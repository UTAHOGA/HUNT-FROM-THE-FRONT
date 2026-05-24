from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2026/pdf/regulations/2026 Big Game Application.pdf"
EXPORTED_PDF = (
    ROOT
    / "processed_data/hard_data_exports/source_pdfs/regulations/2026/2026-big-game-application-guidebook.pdf"
)
MANIFEST = ROOT / "processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json"
RAW_INVENTORY = ROOT / "data_model/quality/raw_pdf_inventory.csv"
RAW_AUDIT = ROOT / "data_model/quality/raw_pdf_inventory_audit.csv"
SOURCE_PATH = "pipeline/RAW/hunt_unit_database/2026/pdf/regulations/2026 Big Game Application.pdf"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _csv_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        matches = [row for row in csv.DictReader(handle) if row.get("path") == SOURCE_PATH]
    assert len(matches) == 1
    return matches[0]


def test_2026_big_game_application_guidebook_is_in_hunting_bible_manifest() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    matches = [row for row in data if row.get("title") == "2026 Big Game Application Guidebook"]

    assert len(matches) == 1
    entry = matches[0]
    assert entry["group"] == "regulation"
    assert entry["type"] == "pdf"
    assert entry["year"] == "2026"
    assert entry["source_authority"] == "Utah Division of Wildlife Resources"
    assert entry["source_role"] == "official_source"
    assert entry["href"] == (
        "./processed_data/hard_data_exports/source_pdfs/regulations/2026/"
        "2026-big-game-application-guidebook.pdf"
    )


def test_2026_big_game_application_export_matches_raw_source() -> None:
    assert SOURCE_PDF.exists()
    assert EXPORTED_PDF.exists()
    assert SOURCE_PDF.stat().st_size == 3_167_332
    assert EXPORTED_PDF.stat().st_size == SOURCE_PDF.stat().st_size
    assert _sha256(EXPORTED_PDF) == _sha256(SOURCE_PDF)


def test_2026_big_game_application_is_reference_only_not_model_input() -> None:
    inventory = _csv_row(RAW_INVENTORY)
    audit = _csv_row(RAW_AUDIT)

    assert inventory["sha256"] == "84e2e3529b527291eb7a8dbe4ab814f6687d719e5c0116fc7dc318756ed9cd75"
    assert inventory["page_count"] == "82"
    assert audit["source_class"] == "regulations"
    assert audit["quality_engine_use"] == "NO"
    assert audit["draw_engine_use"] == "NO"
    assert audit["promotion_status"] != "PROMOTE"
