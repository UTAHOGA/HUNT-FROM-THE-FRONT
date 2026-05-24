from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2025/pdf/regulation/field_regs 2025.pdf"
RAW_INVENTORY = ROOT / "data_model/quality/raw_pdf_inventory.csv"
RAW_AUDIT = ROOT / "data_model/quality/raw_pdf_inventory_audit.csv"
HARD_COPY_MANIFEST = ROOT / "processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json"
CANONICAL_HARD_COPIES = ROOT / "canonical/hard-copies-2026.json"
OUT_DIR = ROOT / "data_truth/regulations_truth/normalized"
REPORT_DIR = ROOT / "processed_data"

SUMMARY = REPORT_DIR / "2025_big_game_field_regulations_source_label_audit.json"
REPORT_MD = REPORT_DIR / "2025_big_game_field_regulations_source_label_audit.md"
CORRECTIONS_CSV = OUT_DIR / "2025_big_game_field_regulations_post_publication_corrections.csv"

SOURCE_PATH = "pipeline/RAW/hunt_unit_database/2025/pdf/regulation/field_regs 2025.pdf"
EXPECTED_SHA256 = "05a87b5babd0a22af62c993bd3fe0ba106fb18f7029ed60fc75f6babe4dbdaa7"
EXPECTED_SIZE_BYTES = 3_432_415


@dataclass(frozen=True)
class Correction:
    correction_type: str
    guidebook_page: str
    correction_date: str
    summary: str


POST_PUBLICATION_CORRECTIONS = [
    Correction(
        "correction",
        "29",
        "2025-12-01",
        "Deleted Salt Lake County restriction bullet for Red Butte Research Natural Area; the area remains closed to public access.",
    ),
    Correction(
        "correction",
        "33",
        "",
        "Removed sentence stating big game may not be donated in the field to align with rule language regarding donations.",
    ),
    Correction(
        "correction",
        "38",
        "",
        "Corrected restricted muzzleloader deer dates to Sept. 24-Oct. 2, 2025 and restricted rifle deer dates to Oct. 18-26, 2025.",
    ),
    Correction(
        "update",
        "guidebook-wide",
        "2025-11-13",
        "Updated recodified Chapter 10 code citations to Chapter 11 and related Utah Code references effective May 7, 2025.",
    ),
    Correction(
        "update",
        "19",
        "",
        "Added youth Uinta Basin private-lands-only permit row and reorganized the youth-only elk permit table and footnotes.",
    ),
    Correction(
        "update",
        "70",
        "",
        "Clarified restricted muzzleloader equipment must meet Utah Admin. Rule R657-5-10(1) and (2).",
    ),
    Correction(
        "update",
        "25-26",
        "",
        "Removed inadvertently included archery-hunt field-possession restriction text from the online edition.",
    ),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_manifest_items(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.get("library", {}).get("items", []))
    return []


def first_pages_text(path: Path, page_count: int = 4) -> str:
    chunks = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:page_count]:
            chunks.append(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
    return "\n".join(chunks)


def write_corrections() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CORRECTIONS_CSV.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "source_file",
            "source_year",
            "source_title",
            "correction_type",
            "guidebook_page",
            "correction_date",
            "summary",
            "classification",
            "modeling_guardrail",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for correction in POST_PUBLICATION_CORRECTIONS:
            writer.writerow(
                {
                    "source_file": SOURCE_PATH,
                    "source_year": "2025",
                    "source_title": "2025 Utah Big Game Field Regulations",
                    "correction_type": correction.correction_type,
                    "guidebook_page": correction.guidebook_page,
                    "correction_date": correction.correction_date,
                    "summary": correction.summary,
                    "classification": "REGULATION_REFERENCE_ONLY",
                    "modeling_guardrail": "DO_NOT_USE_AS_DRAW_ODDS_HARVEST_FEATURE_OR_2026_QUOTA_INPUT",
                }
            )


def build_summary() -> dict[str, object]:
    source_exists = SOURCE_PDF.exists()
    source_hash = sha256(SOURCE_PDF) if source_exists else ""
    source_size = SOURCE_PDF.stat().st_size if source_exists else 0
    text = first_pages_text(SOURCE_PDF) if source_exists else ""
    compact_text = " ".join(text.split()).upper()

    raw_inventory_rows = [row for row in read_csv_rows(RAW_INVENTORY) if row.get("path") == SOURCE_PATH]
    raw_audit_rows = [row for row in read_csv_rows(RAW_AUDIT) if row.get("path") == SOURCE_PATH]
    manifest_items = read_manifest_items(HARD_COPY_MANIFEST)
    canonical_items = read_manifest_items(CANONICAL_HARD_COPIES)
    all_manifest_items = manifest_items + canonical_items

    field_reg_items = [
        item
        for item in all_manifest_items
        if "field" in json.dumps(item, sort_keys=True).lower()
        and "regulation" in json.dumps(item, sort_keys=True).lower()
    ]
    mislabeled_2026_items = [
        item
        for item in field_reg_items
        if "2026" in str(item.get("title", ""))
        or "/regulations/2026/" in str(item.get("href", ""))
        or "source_pdfs/regulations/2026" in str(item.get("href", ""))
    ]

    checks = {
        "source_pdf_exists": source_exists,
        "source_path_is_2025_folder": "/2025/" in SOURCE_PATH.replace("\\", "/"),
        "source_hash_matches_expected": source_hash == EXPECTED_SHA256,
        "source_size_matches_expected": source_size == EXPECTED_SIZE_BYTES,
        "text_mentions_2025_field_regulations": (
            "UTAH BIG GAME FIELD REGULATIONS" in compact_text and "2025" in compact_text
        ),
        "text_does_not_identify_as_2026": "UTAH BIG GAME FIELD REGULATIONS" in compact_text
        and "2026" not in compact_text[:500],
        "not_in_quality_raw_inventory": len(raw_inventory_rows) == 0,
        "not_promoted_by_quality_or_draw_audit": len(raw_audit_rows) == 0,
        "no_2026_field_regulations_manifest_label": len(mislabeled_2026_items) == 0,
    }

    status_counts = Counter("PASS" if passed else "REVIEW" for passed in checks.values())
    return {
        "source_file": SOURCE_PATH,
        "expected_title": "2025 Utah Big Game Field Regulations",
        "expected_source_year": "2025",
        "actual_sha256": source_hash,
        "expected_sha256": EXPECTED_SHA256,
        "actual_size_bytes": source_size,
        "expected_size_bytes": EXPECTED_SIZE_BYTES,
        "classification": "REGULATION_REFERENCE_ONLY",
        "modeling_guardrail": "DO_NOT_USE_AS_DRAW_ODDS_HARVEST_FEATURE_OR_2026_QUOTA_INPUT",
        "source_inventory_status": "NOT_IN_QUALITY_RAW_INVENTORY",
        "library_export_status": "NOT_EXPORTED_TO_HUNTING_BIBLE",
        "post_publication_correction_count": len(POST_PUBLICATION_CORRECTIONS),
        "manifest_field_regulation_items_found": len(field_reg_items),
        "mislabeled_2026_manifest_items": len(mislabeled_2026_items),
        "checks": checks,
        "status_counts": dict(status_counts),
        "audit_blocker_count": status_counts.get("REVIEW", 0),
    }


def write_markdown(summary: dict[str, object]) -> None:
    lines = [
        "# 2025 Big Game Field Regulations Source Label Audit",
        "",
        f"Source PDF: `{summary['source_file']}`",
        "",
        "This audit locks the file identity as 2025 field regulations only. It does not promote the file into draw odds, harvest features, quota math, or prediction math.",
        "",
        "## Summary",
        "",
        f"- Expected title: `{summary['expected_title']}`",
        f"- Expected source year: `{summary['expected_source_year']}`",
        f"- SHA-256: `{summary['actual_sha256']}`",
        f"- Library export status: `{summary['library_export_status']}`",
        f"- Mislabeled 2026 manifest items: `{summary['mislabeled_2026_manifest_items']}`",
        f"- Post-publication corrections captured: `{summary['post_publication_correction_count']}`",
        f"- Audit blockers: `{summary['audit_blocker_count']}`",
        "",
        "## Checks",
        "",
        "| check | status |",
        "|---|---:|",
    ]
    for check, passed in summary["checks"].items():
        lines.append(f"| {check} | {'PASS' if passed else 'REVIEW'} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_corrections()
    summary = build_summary()
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
