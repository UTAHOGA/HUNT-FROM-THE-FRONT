from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "processed_data/2025_big_game_field_regulations_source_label_audit.json"
CORRECTIONS = (
    ROOT
    / "data_truth/regulations_truth/normalized/2025_big_game_field_regulations_post_publication_corrections.csv"
)


def _run_audit() -> None:
    subprocess.run([sys.executable, "scripts/audit-big-game-field-regulations-2025.py"], cwd=ROOT, check=True)


def test_2025_field_regulations_source_label_audit_passes() -> None:
    _run_audit()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["source_file"] == "pipeline/RAW/hunt_unit_database/2025/pdf/regulation/field_regs 2025.pdf"
    assert summary["expected_title"] == "2025 Utah Big Game Field Regulations"
    assert summary["expected_source_year"] == "2025"
    assert summary["actual_sha256"] == "05a87b5babd0a22af62c993bd3fe0ba106fb18f7029ed60fc75f6babe4dbdaa7"
    assert summary["classification"] == "REGULATION_REFERENCE_ONLY"
    assert summary["modeling_guardrail"] == "DO_NOT_USE_AS_DRAW_ODDS_HARVEST_FEATURE_OR_2026_QUOTA_INPUT"
    assert summary["mislabeled_2026_manifest_items"] == 0
    assert summary["audit_blocker_count"] == 0
    assert all(summary["checks"].values())


def test_2025_field_regulations_post_publication_corrections_are_captured() -> None:
    _run_audit()

    with CORRECTIONS.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 7
    assert {row["source_year"] for row in rows} == {"2025"}
    assert {row["source_title"] for row in rows} == {"2025 Utah Big Game Field Regulations"}
    assert all(row["classification"] == "REGULATION_REFERENCE_ONLY" for row in rows)
    assert any(row["guidebook_page"] == "38" and "restricted muzzleloader" in row["summary"] for row in rows)
    assert any(row["guidebook_page"] == "25-26" and "archery-hunt" in row["summary"] for row in rows)
