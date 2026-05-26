#!/usr/bin/env python3
"""Lock reviewed current-reference-only 2026 hunt codes.

These rows are valid current reference rows, not historical-code failures. The
script records that review, promotes the Cougar statewide unlimited permit text
from the DWR Hunt Planner source, and writes a small mapping-law audit artifact.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
COUGAR_SOURCE_PATH = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_cougar.csv"
EXTENDED_ELK_SOURCE_PATH = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_elk_archery_extended.csv"
PRIVATE_DEER_LOCK_PATH = ROOT / "data_truth/permit_overlay_truth/normalized/private_land_deer_hunt_code_lock_2026.csv"
PRIVATE_ELK_SOURCE_PATH = (
    ROOT
    / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/"
    / "2026 l.e. elk.private lands  EL-2025 and LO-2026.csv"
)

REVIEW_OUTPUT_PATH = (
    ROOT / "data_truth/crosswalk_truth/validation/current_reference_codes_2026_review.csv"
)
SUMMARY_OUTPUT_PATH = (
    ROOT / "data_truth/crosswalk_truth/validation/current_reference_codes_2026_summary.json"
)
MARKDOWN_OUTPUT_PATH = ROOT / "processed_data/current_reference_codes_2026_review.md"

REVIEWED_CODES = {
    "CG9999": {
        "expected": {
            "hunt_name": "Cougar - Statewide",
            "sex_type": "Either Sex",
            "species": "Cougar",
            "weapon": "Any Legal Weapon",
            "hunt_type": "Statewide",
            "boundary_id": "5107",
        },
        "source_file": COUGAR_SOURCE_PATH,
        "permit_status": "UNLIMITED_PERMITS",
        "review_note": "Reviewed current statewide cougar reference row; DWR source publishes unlimited permits and no resident/nonresident split.",
    },
    "EX1000": {
        "expected": {
            "hunt_name": "Elk Extended Archery",
            "sex_type": "Hunters Choice",
            "species": "Elk",
            "weapon": "Archery",
            "hunt_type": "Extended Archery",
            "boundary_id": "5130",
        },
        "source_file": EXTENDED_ELK_SOURCE_PATH,
        "permit_status": "NO_QUOTA_PUBLISHED",
        "review_note": "Reviewed current extended-archery elk reference row; no numeric permit quota is published.",
    },
    "LO0008": {
        "expected": {
            "hunt_name": "Diamond Mtn Landowner Association",
            "sex_type": "Buck",
            "species": "Deer",
            "weapon": "Archery",
            "hunt_type": "Limited Entry - Private Land Only",
            "boundary_id": "206",
        },
        "source_file": PRIVATE_DEER_LOCK_PATH,
        "permit_status": "NO_QUOTA_PUBLISHED",
        "review_note": "Reviewed Diamond Mtn LOA buck deer archery reference row; no public permit quota is published.",
    },
    "LO0011": {
        "expected": {
            "hunt_name": "Diamond Mtn Landowner Association",
            "sex_type": "Bull",
            "species": "Elk",
            "weapon": "Archery",
            "hunt_type": "Limited Entry - Private Land Only",
            "boundary_id": "206",
        },
        "source_file": PRIVATE_ELK_SOURCE_PATH,
        "permit_status": "NO_QUOTA_PUBLISHED",
        "review_note": "Reviewed Diamond Mtn LOA bull elk archery reference row; no public/private-land permit quota is published.",
    },
}

REVIEW_COLUMNS = [
    "hunt_code",
    "boundary_id",
    "hunt_code_mapping_status",
    "boundary_id_mapping_status",
    "candidate_hunt_code",
    "candidate_boundary_id",
    "hunt_name",
    "sex_type",
    "species",
    "weapon",
    "hunt_type",
    "season",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "permit_allotment_2026_res",
    "permit_allotment_2026_nr",
    "permit_allotment_2026_total",
    "permit_allotment_2026_status",
    "review_status",
    "source_file",
    "source_sha256",
    "review_note",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_lookup(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return {row.get("hunt_code", ""): row for row in read_csv(path) if row.get("hunt_code")}


def validate_expected(code: str, row: dict[str, str], expected: dict[str, str]) -> list[str]:
    errors = []
    for field, expected_value in expected.items():
        if row.get(field, "") != expected_value:
            errors.append(f"{code} {field}: expected {expected_value!r}, found {row.get(field, '')!r}")
    return errors


def update_database(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    rows_by_code = {row["hunt_code"]: row for row in rows}
    errors: list[str] = []
    cougar_source = source_lookup(COUGAR_SOURCE_PATH).get("CG9999", {})

    for code, config in REVIEWED_CODES.items():
        if code not in rows_by_code:
            errors.append(f"{code} missing from DATABASE.csv")
            continue
        errors.extend(validate_expected(code, rows_by_code[code], config["expected"]))

    if errors:
        return rows, errors

    if not cougar_source:
        errors.append("CG9999 missing from 2026_cougar.csv")
        return rows, errors

    cg = rows_by_code["CG9999"]
    cg["season"] = cougar_source.get("season", "open")
    cg["permits_2026_res"] = ""
    cg["permits_2026_nr"] = ""
    cg["permits_2026_total"] = cougar_source.get("permits_2026_total", "unlimited")
    cg["permits_2026_source"] = "Utah DWR Hunt Planner"
    cg["permit_allotment_2026_res"] = ""
    cg["permit_allotment_2026_nr"] = ""
    cg["permit_allotment_2026_total"] = cougar_source.get("permits_2026_total", "unlimited")
    cg["permit_allotment_2026_source"] = "Utah DWR Hunt Planner"
    cg["permit_allotment_2026_source_file"] = str(COUGAR_SOURCE_PATH.relative_to(ROOT)).replace("\\", "/")
    cg["permit_allotment_2026_status"] = "UNLIMITED_PERMITS"
    return rows, errors


def build_review_rows(database_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows_by_code = {row["hunt_code"]: row for row in database_rows}
    review_rows: list[dict[str, str]] = []
    for code, config in REVIEWED_CODES.items():
        row = rows_by_code[code]
        source_path: Path = config["source_file"]
        review_rows.append(
            {
                "hunt_code": code,
                "boundary_id": row.get("boundary_id", ""),
                "hunt_code_mapping_status": "REVIEWED_CURRENT_REFERENCE",
                "boundary_id_mapping_status": "REVIEWED_CURRENT_REFERENCE",
                "candidate_hunt_code": code,
                "candidate_boundary_id": row.get("boundary_id", ""),
                "hunt_name": row.get("hunt_name", ""),
                "sex_type": row.get("sex_type", ""),
                "species": row.get("species", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "season": row.get("season", ""),
                "permits_2026_res": row.get("permits_2026_res", ""),
                "permits_2026_nr": row.get("permits_2026_nr", ""),
                "permits_2026_total": row.get("permits_2026_total", ""),
                "permit_allotment_2026_res": row.get("permit_allotment_2026_res", ""),
                "permit_allotment_2026_nr": row.get("permit_allotment_2026_nr", ""),
                "permit_allotment_2026_total": row.get("permit_allotment_2026_total", ""),
                "permit_allotment_2026_status": row.get("permit_allotment_2026_status", ""),
                "review_status": config["permit_status"],
                "source_file": str(source_path.relative_to(ROOT)).replace("\\", "/"),
                "source_sha256": sha256(source_path) if source_path.exists() else "",
                "review_note": config["review_note"],
            }
        )
    return review_rows


def write_database(rows: list[dict[str, str]], columns: list[str]) -> None:
    with DATABASE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(review_rows: list[dict[str, str]], summary: dict[str, object]) -> None:
    MARKDOWN_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Current Reference Codes 2026 Review",
        "",
        "These rows are valid current reference rows and should not be treated as missing crosswalk failures.",
        "",
        f"- Reviewed rows: {summary['reviewed_count']}",
        f"- Unlimited permit rows: {summary['unlimited_permit_count']}",
        f"- Blockers: {summary['blocker_count']}",
        "",
        "## Rows",
        "",
    ]
    for row in review_rows:
        total = row["permits_2026_total"] or "(none)"
        lines.append(
            f"- {row['hunt_code']}: {row['hunt_name']}; {row['review_status']}; total permits {total}"
        )
    MARKDOWN_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    database_rows = read_csv(DATABASE_PATH)
    with DATABASE_PATH.open("r", newline="", encoding="utf-8-sig") as handle:
        columns = csv.DictReader(handle).fieldnames or []

    updated_rows, errors = update_database(database_rows)
    if errors:
        summary = {
            "artifact": "current_reference_codes_2026_review",
            "reviewed_count": 0,
            "unlimited_permit_count": 0,
            "blocker_count": len(errors),
            "blockers": errors,
        }
        SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_OUTPUT_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise SystemExit("\n".join(errors))

    write_database(updated_rows, columns)
    review_rows = build_review_rows(updated_rows)
    write_csv(REVIEW_OUTPUT_PATH, review_rows, REVIEW_COLUMNS)
    summary = {
        "artifact": "current_reference_codes_2026_review",
        "database_source": str(DATABASE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "reviewed_count": len(review_rows),
        "reviewed_codes": [row["hunt_code"] for row in review_rows],
        "unlimited_permit_count": sum(1 for row in review_rows if row["review_status"] == "UNLIMITED_PERMITS"),
        "no_quota_published_count": sum(1 for row in review_rows if row["review_status"] == "NO_QUOTA_PUBLISHED"),
        "blocker_count": 0,
        "blockers": [],
    }
    SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUTPUT_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(review_rows, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
