from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "data_truth/comparison_outputs/validation/final_permit_database_crosscheck_2026_summary.json"
SPECIES = ROOT / "data_truth/comparison_outputs/validation/final_permit_database_crosscheck_2026_by_species.csv"
PREFIX = ROOT / "data_truth/comparison_outputs/validation/final_permit_database_crosscheck_2026_by_prefix.csv"


def _csv_by_key(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row[key]: row for row in csv.DictReader(handle)}


def test_final_permit_crosscheck_has_no_identity_or_total_blockers() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    assert summary["database_row_count"] == 1394
    assert summary["unique_hunt_code_count"] == 1394
    assert summary["duplicate_hunt_code_count"] == 0
    assert summary["blank_boundary_id_count"] == 0
    assert summary["permit_vs_allotment_total_mismatch_count"] == 0
    assert summary["live_comparison_status_counts"]["MATCH"] == 1068
    assert "TOTAL_MATCH_SPLIT_DIFFERS" not in summary["live_comparison_status_counts"]
    assert summary["field_populated_counts"] == {
        "permit_allotment_2026_total": 1091,
        "permits_2025_draw_total": 627,
        "permits_2025_total": 1030,
        "permits_2026_total": 1120,
    }


def test_final_permit_crosscheck_species_and_prefix_counts_are_stable() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    species = _csv_by_key(SPECIES, "species")
    prefixes = _csv_by_key(PREFIX, "prefix")

    assert summary["species_counts"] == {
        "Bison": 19,
        "Black Bear": 106,
        "Cougar": 1,
        "Deer": 479,
        "Desert Bighorn Sheep": 25,
        "Elk": 558,
        "Moose": 32,
        "Mountain Goat": 18,
        "Pronghorn": 117,
        "Rocky Mountain Bighorn Sheep": 21,
        "Turkey": 18,
    }
    assert species["Elk"]["hunt_code_count"] == "558"
    assert species["Deer"]["hunt_code_count"] == "479"
    assert prefixes["EB"]["hunt_code_count"] == "222"
    assert prefixes["EA"]["hunt_code_count"] == "204"
    assert prefixes["LO"]["hunt_code_count"] == "113"
