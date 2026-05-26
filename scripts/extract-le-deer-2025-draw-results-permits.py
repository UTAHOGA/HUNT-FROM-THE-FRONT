"""Extract 2025 Utah limited-entry deer draw-results permit totals.

The source PDF is a completed 2025 draw-results file stored under the 2026
folder for model-target-year use. Per project year rules:

- reported_draw_year = 2025
- model_target_year = 2026
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2026/pdf/draw_odds/2025 LE Deer Draw Results.pdf"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"

REPORTED_DRAW_YEAR = 2025
MODEL_TARGET_YEAR = 2026

NORMALIZED_OUT = (
    ROOT / "data_truth/draw_results_truth/normalized/le_deer_2025_draw_results_model_target_2026_permit_totals.csv"
)
VALIDATION_OUT = (
    ROOT / "data_truth/draw_results_truth/validation/le_deer_2025_draw_results_model_target_2026_vs_DATABASE.csv"
)
SUMMARY_OUT = ROOT / "data_truth/draw_results_truth/validation/le_deer_2025_draw_results_model_target_2026_summary.json"
REPORT_OUT = ROOT / "processed_data/le_deer_2025_draw_results_model_target_2026_permit_totals.md"

SOURCE_CLASSIFICATION = "LIMITED_ENTRY_DEER_BONUS_DRAW"
TOTALS_PATTERN = re.compile(
    r"Totals\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(?:(?:1\s+)?in\s+[\d.]+|N\s*/?\s*A|N/A)"
)

NORMALIZED_FIELDS = [
    "hunt_code",
    "boundary_id",
    "hunt_code_mapping_status",
    "boundary_id_mapping_status",
    "candidate_hunt_code",
    "candidate_boundary_id",
    "hunt_name",
    "raw_hunt_name",
    "species",
    "sex_type",
    "weapon",
    "reported_draw_year",
    "model_target_year",
    "source_file",
    "source_sha256",
    "pdf_page_number",
    "source_report_page",
    "resident_eligible_applicants",
    "resident_bonus_permits",
    "resident_regular_permits",
    "resident_total_permits",
    "nonresident_eligible_applicants",
    "nonresident_bonus_permits",
    "nonresident_regular_permits",
    "nonresident_total_permits",
    "total_public_draw_permits",
    "source_classification",
]

VALIDATION_FIELDS = NORMALIZED_FIELDS + [
    "database_hunt_name",
    "database_species",
    "database_weapon",
    "database_hunt_type",
    "database_permits_2025_draw_res",
    "database_permits_2025_draw_nr",
    "database_permits_2025_draw_total",
    "database_permits_2025_draw_source",
    "database_permits_2025_res",
    "database_permits_2025_nr",
    "database_permits_2025_total",
    "database_comparison_status",
    "review_note",
]


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]
        return rows, [(field or "").strip() for field in (reader.fieldnames or [])]


def write_csv(path: Path, rows: Iterable[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_text(text: str) -> str:
    text = (text or "").replace("\u2013", "-").replace("\u2014", "-").replace("\u00a0", " ")
    text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace(" -An y ", " - Any ")
    return re.sub(r"\s+", " ", text).strip()


def infer_weapon(raw_hunt_name: str) -> str:
    cleaned = normalize_text(raw_hunt_name)
    for weapon in [
        "Any Legal Weapon",
        "Archery",
        "Muzzleloader",
        "Multiseason",
        "Restricted Rifle",
        "Restricted Archery",
        "Restricted Muzzleloader",
        "Restricted Multiseason",
    ]:
        if cleaned.lower().endswith(f" - {weapon}".lower()):
            return weapon
    return ""


def infer_hunt_name(raw_hunt_name: str) -> str:
    cleaned = normalize_text(raw_hunt_name)
    weapon = infer_weapon(cleaned)
    if weapon:
        cleaned = re.sub(rf"\s+-\s+{re.escape(weapon)}$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(
        r"^(Premium\s+Le|Le|Cwmu|Management|Cactus|Expo)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"^(Archery|Alw \(rifle\)|Muzzleloader|Multiseason)\s+Buck Deer\s+-\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^Buck Deer\s+-\s+", "", cleaned, flags=re.I)
    return cleaned


def load_database() -> dict[str, dict[str, str]]:
    rows, _ = read_csv(DATABASE)
    return {row.get("hunt_code", "").upper(): row for row in rows if row.get("hunt_code")}


def parse_pdf(database_by_code: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    reader = PdfReader(str(SOURCE_PDF))
    source_hash = sha256(SOURCE_PDF)
    source_rel = str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/")
    rows: list[dict[str, object]] = []
    missing_header_pages: list[int] = []

    for pdf_page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        hunt_match = re.search(r"Hunt:\s*([A-Z]{2}\d{4})\s+(.+?)\s+Page\s+(\d+)", text, re.S)
        if not hunt_match:
            missing_header_pages.append(pdf_page_number)
            continue
        totals = TOTALS_PATTERN.findall(text)
        if len(totals) < 2:
            raise RuntimeError(f"Could not extract resident/nonresident totals on PDF page {pdf_page_number}")

        code = hunt_match.group(1).strip().upper()
        raw_name = normalize_text(hunt_match.group(2))
        resident = tuple(int(value) for value in totals[0])
        nonresident = tuple(int(value) for value in totals[1])
        db = database_by_code.get(code, {})
        rows.append(
            {
                "hunt_code": code,
                "boundary_id": db.get("boundary_id", ""),
                "hunt_code_mapping_status": "REVIEWED_CURRENT_HUNT_CODE" if db else "SOURCE_CODE_NOT_IN_DATABASE",
                "boundary_id_mapping_status": "DATABASE_BOUNDARY_ID" if db.get("boundary_id") else "BOUNDARY_ID_MISSING",
                "candidate_hunt_code": code,
                "candidate_boundary_id": db.get("boundary_id", ""),
                "hunt_name": infer_hunt_name(raw_name),
                "raw_hunt_name": raw_name,
                "species": "Deer",
                "sex_type": "Buck",
                "weapon": infer_weapon(raw_name),
                "reported_draw_year": REPORTED_DRAW_YEAR,
                "model_target_year": MODEL_TARGET_YEAR,
                "source_file": source_rel,
                "source_sha256": source_hash,
                "pdf_page_number": pdf_page_number,
                "source_report_page": hunt_match.group(3),
                "resident_eligible_applicants": resident[0],
                "resident_bonus_permits": resident[1],
                "resident_regular_permits": resident[2],
                "resident_total_permits": resident[3],
                "nonresident_eligible_applicants": nonresident[0],
                "nonresident_bonus_permits": nonresident[1],
                "nonresident_regular_permits": nonresident[2],
                "nonresident_total_permits": nonresident[3],
                "total_public_draw_permits": resident[3] + nonresident[3],
                "source_classification": SOURCE_CLASSIFICATION,
            }
        )
    if missing_header_pages != [1]:
        raise RuntimeError(f"Unexpected pages without Hunt header: {missing_header_pages}")
    return rows


def as_int_text(value: object) -> str:
    text = str(value or "").strip()
    if text == "":
        return ""
    return str(int(float(text.replace(",", ""))))


def compare_database(rows: list[dict[str, object]], database_by_code: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in rows:
        code = str(row["hunt_code"])
        db = database_by_code.get(code, {})
        source_res = str(row["resident_total_permits"])
        source_nr = str(row["nonresident_total_permits"])
        source_total = str(row["total_public_draw_permits"])
        db_draw_res = as_int_text(db.get("permits_2025_draw_res"))
        db_draw_nr = as_int_text(db.get("permits_2025_draw_nr"))
        db_draw_total = as_int_text(db.get("permits_2025_draw_total"))
        db_2025_res = as_int_text(db.get("permits_2025_res"))
        db_2025_nr = as_int_text(db.get("permits_2025_nr"))
        db_2025_total = as_int_text(db.get("permits_2025_total"))

        if not db:
            status = "MISSING_DATABASE_ROW"
            note = "Draw-results hunt code does not exist in current DATABASE.csv."
        elif (db_draw_res, db_draw_nr, db_draw_total) == (source_res, source_nr, source_total):
            status = "MATCH_DATABASE_2025_DRAW_FIELDS"
            note = "Source draw-result totals match canonical DATABASE.csv 2025 draw fields."
        elif (db_2025_res, db_2025_nr, db_2025_total) == (source_res, source_nr, source_total):
            status = "MATCH_DATABASE_2025_PERMIT_FIELDS"
            note = "Source draw-result totals match canonical DATABASE.csv 2025 permit fields."
        elif (db_draw_res, db_draw_nr, db_draw_total) == ("", "", "") and (
            db_2025_res,
            db_2025_nr,
            db_2025_total,
        ) == ("", "", ""):
            status = "DATABASE_2025_FIELDS_BLANK"
            note = "Current DATABASE.csv row exists but has no 2025 draw or permit values for this source row."
        else:
            status = "PROTECTED_DATABASE_DIFFERENCE"
            note = "Do not overwrite DATABASE.csv without reviewed lineage repair."

        out = dict(row)
        out.update(
            {
                "database_hunt_name": db.get("hunt_name", ""),
                "database_species": db.get("species", ""),
                "database_weapon": db.get("weapon", ""),
                "database_hunt_type": db.get("hunt_type", ""),
                "database_permits_2025_draw_res": db_draw_res,
                "database_permits_2025_draw_nr": db_draw_nr,
                "database_permits_2025_draw_total": db_draw_total,
                "database_permits_2025_draw_source": db.get("permits_2025_draw_source", ""),
                "database_permits_2025_res": db_2025_res,
                "database_permits_2025_nr": db_2025_nr,
                "database_permits_2025_total": db_2025_total,
                "database_comparison_status": status,
                "review_note": note,
            }
        )
        output.append(out)
    return output


def write_report(summary: dict[str, object]) -> None:
    lines = [
        "# 2025 LE Deer Draw Results Extraction",
        "",
        "Extracted completed 2025 limited-entry deer draw-result permit totals for model target year 2026.",
        "",
        f"- PDF pages: {summary['pdf_pages']}",
        f"- Extracted hunt-code rows: {summary['source_rows']}",
        f"- Unique hunt codes: {summary['unique_hunt_codes']}",
        f"- Total public draw permits: {summary['source_total_public_draw_permits']}",
        f"- DATABASE matches: {summary['database_match_count']}",
        f"- DATABASE numeric differences: {summary['database_difference_count']}",
        f"- Source codes missing from current DATABASE.csv: {summary['missing_database_row_count']}",
        "",
        "No current 2026 DATABASE.csv permit/allotment cells were changed by this extraction.",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    database_by_code = load_database()
    rows = parse_pdf(database_by_code)
    codes = [str(row["hunt_code"]) for row in rows]
    duplicates = sorted(code for code, count in Counter(codes).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate LE deer draw-result hunt codes: {duplicates}")

    validation = compare_database(rows, database_by_code)
    write_csv(NORMALIZED_OUT, rows, NORMALIZED_FIELDS)
    write_csv(VALIDATION_OUT, validation, VALIDATION_FIELDS)

    status_counts = Counter(row["database_comparison_status"] for row in validation)
    match_count = sum(
        status_counts[status]
        for status in [
            "MATCH_DATABASE_2025_DRAW_FIELDS",
            "MATCH_DATABASE_2025_PERMIT_FIELDS",
        ]
    )
    summary = {
        "artifact": "le_deer_2025_draw_results_model_target_2026_permit_totals",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_file": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(SOURCE_PDF),
        "reported_draw_year": REPORTED_DRAW_YEAR,
        "model_target_year": MODEL_TARGET_YEAR,
        "pdf_pages": len(PdfReader(str(SOURCE_PDF)).pages),
        "source_rows": len(rows),
        "unique_hunt_codes": len(set(codes)),
        "source_total_public_draw_permits": sum(int(row["total_public_draw_permits"]) for row in rows),
        "resident_total_draw_permits": sum(int(row["resident_total_permits"]) for row in rows),
        "nonresident_total_draw_permits": sum(int(row["nonresident_total_permits"]) for row in rows),
        "database_status_counts": dict(sorted(status_counts.items())),
        "database_match_count": match_count,
        "database_difference_count": status_counts["PROTECTED_DATABASE_DIFFERENCE"],
        "missing_database_row_count": status_counts["MISSING_DATABASE_ROW"],
        "missing_database_codes": [
            row["hunt_code"] for row in validation if row["database_comparison_status"] == "MISSING_DATABASE_ROW"
        ],
        "outputs": {
            "normalized": str(NORMALIZED_OUT.relative_to(ROOT)).replace("\\", "/"),
            "validation": str(VALIDATION_OUT.relative_to(ROOT)).replace("\\", "/"),
            "report": str(REPORT_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "guardrail": "No current 2026 DATABASE.csv permit/allotment cells were changed by this extraction.",
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_report(summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
