"""Extract 2025 Utah once-in-a-lifetime draw-results permit totals.

The source PDF is a completed 2025 O.I.L. draw-results file stored under the
2026 folder for model-target-year use. Per project year rules:

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
SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2026/pdf/draw_odds/2025 O.I.L. Draw Results.pdf"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"

REPORTED_DRAW_YEAR = 2025
MODEL_TARGET_YEAR = 2026

NORMALIZED_OUT = (
    ROOT / "data_truth/draw_results_truth/normalized/oil_2025_draw_results_model_target_2026_permit_totals.csv"
)
VALIDATION_OUT = (
    ROOT / "data_truth/draw_results_truth/validation/oil_2025_draw_results_model_target_2026_vs_DATABASE.csv"
)
SUMMARY_OUT = ROOT / "data_truth/draw_results_truth/validation/oil_2025_draw_results_model_target_2026_summary.json"
REPORT_OUT = ROOT / "processed_data/oil_2025_draw_results_model_target_2026_permit_totals.md"

SPECIES_BY_PREFIX = {
    "BI": "Bison",
    "DS": "Desert Bighorn Sheep",
    "GO": "Mountain Goat",
    "MB": "Moose",
    "RS": "Rocky Mountain Bighorn Sheep",
}

SEX_BY_PREFIX = {
    "BI": "Hunters Choice",
    "DS": "Male Only",
    "GO": "Either Sex",
    "MB": "Bull",
    "RS": "Ram",
}

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


def prefix(code: str) -> str:
    return re.match(r"^[A-Z]+", code).group(0)


def normalize_name(text: str) -> str:
    return " ".join((text or "").replace(" -An y ", " - Any ").replace("-Fillmore", "- Fillmore").split())


def infer_weapon(raw_hunt_name: str) -> str:
    cleaned = normalize_name(raw_hunt_name)
    if cleaned.endswith(" - Archery"):
        return "Archery"
    if cleaned.endswith(" - Any Legal Weapon"):
        return "Any Legal Weapon"
    return ""


def infer_hunt_name(code: str, raw_hunt_name: str) -> str:
    cleaned = normalize_name(raw_hunt_name)
    weapon = infer_weapon(cleaned)
    if weapon:
        cleaned = re.sub(rf"\s+-\s+{re.escape(weapon)}$", "", cleaned).strip()

    code_prefix = prefix(code)
    species_label = SPECIES_BY_PREFIX.get(code_prefix, "")
    if code_prefix == "MB":
        cleaned = re.sub(r"^Bull Moose\s+-\s+", "", cleaned).strip()
    elif code_prefix == "BI":
        cleaned = re.sub(r"^Bison\s*\([^)]*Choice\)\s+-\s+", "", cleaned, flags=re.IGNORECASE).strip()
    elif code_prefix == "DS":
        cleaned = re.sub(r"^Desert Bighorn Sheep(?:\s+Archery)?\s+-\s*", "", cleaned).strip()
    elif code_prefix == "RS":
        cleaned = re.sub(r"^Rocky Mountain Bighorn Sheep(?:\s+Archery)?\s+-\s*", "", cleaned).strip()
    elif code_prefix == "GO":
        cleaned = re.sub(r"^Mountain Goat\s+-\s+", "", cleaned).strip()
    elif species_label and cleaned.startswith(species_label):
        cleaned = cleaned[len(species_label) :].strip(" -")
    return cleaned


def load_database() -> dict[str, dict[str, str]]:
    rows, _ = read_csv(DATABASE)
    return {row.get("hunt_code", "").upper(): row for row in rows if row.get("hunt_code")}


def parse_pdf(database_by_code: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    reader = PdfReader(str(SOURCE_PDF))
    source_hash = sha256(SOURCE_PDF)
    source_rel = str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/")
    rows: list[dict[str, object]] = []

    for pdf_page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        hunt_match = re.search(r"Hunt:\s*([A-Z]{2}\d{4})\s+(.+?)\s+Page\s+(\d+)", text, re.S)
        if not hunt_match:
            raise RuntimeError(f"Could not extract Hunt header on PDF page {pdf_page_number}")
        totals = TOTALS_PATTERN.findall(text)
        if len(totals) < 2:
            raise RuntimeError(f"Could not extract resident/nonresident totals on PDF page {pdf_page_number}")

        code = hunt_match.group(1).strip().upper()
        raw_name = normalize_name(hunt_match.group(2))
        code_prefix = prefix(code)
        resident = tuple(int(value) for value in totals[0])
        nonresident = tuple(int(value) for value in totals[1])
        db = database_by_code.get(code, {})
        rows.append(
            {
                "hunt_code": code,
                "boundary_id": db.get("boundary_id", ""),
                "hunt_code_mapping_status": "REVIEWED_CURRENT_HUNT_CODE"
                if db
                else "SOURCE_CODE_NOT_IN_DATABASE",
                "boundary_id_mapping_status": "DATABASE_BOUNDARY_ID"
                if db.get("boundary_id")
                else "BOUNDARY_ID_MISSING",
                "candidate_hunt_code": code,
                "candidate_boundary_id": db.get("boundary_id", ""),
                "hunt_name": infer_hunt_name(code, raw_name),
                "raw_hunt_name": raw_name,
                "species": SPECIES_BY_PREFIX.get(code_prefix, ""),
                "sex_type": SEX_BY_PREFIX.get(code_prefix, ""),
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
                "source_classification": f"{SPECIES_BY_PREFIX.get(code_prefix, code_prefix).upper()}_OIL_BONUS_DRAW",
            }
        )
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
            status = "MATCH_DATABASE_2025_DRAW_PERMITS"
            note = "Source totals match DATABASE.csv 2025 draw-results permit fields."
        elif not (db_draw_res or db_draw_nr or db_draw_total):
            status = "DATABASE_2025_DRAW_PERMITS_BLANK"
            note = "Source has draw-results totals; DATABASE.csv has blank 2025 draw-results fields."
        else:
            status = "DIFFERS_FROM_DATABASE_2025_DRAW_PERMITS"
            note = "Do not overwrite automatically; historical draw-results lineage must be reviewed."

        output.append(
            {
                **row,
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
    return output


def build_report(summary: dict[str, object]) -> str:
    lines = [
        "# 2025 O.I.L. Draw Results Permit Totals",
        "",
        f"- Source PDF: `{summary['source_file']}`",
        f"- Reported draw year: `{summary['reported_draw_year']}`",
        f"- Model target year: `{summary['model_target_year']}`",
        f"- Hunt-code rows extracted: `{summary['source_rows']}`",
        f"- Total public draw permits in source: `{summary['source_total_public_draw_permits']}`",
        f"- DATABASE matches: `{summary['database_match_count']}`",
        f"- DATABASE differences requiring review: `{summary['database_difference_count']}`",
        f"- DATABASE blank draw fields: `{summary['database_blank_count']}`",
        f"- DATABASE missing codes: `{summary['database_missing_codes']}`",
        "",
        "This is historical draw-results evidence for model target year 2026. It must not be promoted into current 2026 permit availability fields.",
        "",
        "## Prefix Counts",
        "",
    ]
    for prefix_code, count in sorted(summary["prefix_counts"].items()):
        lines.append(f"- {prefix_code}: {count}")
    return "\n".join(lines) + "\n"


def main() -> None:
    database_by_code = load_database()
    rows = parse_pdf(database_by_code)
    duplicate_codes = sorted(code for code, count in Counter(str(row["hunt_code"]) for row in rows).items() if count > 1)
    if duplicate_codes:
        raise RuntimeError(f"Duplicate O.I.L. hunt codes found: {duplicate_codes}")

    validation_rows = compare_database(rows, database_by_code)
    status_counts = Counter(str(row["database_comparison_status"]) for row in validation_rows)
    prefix_counts = Counter(prefix(str(row["hunt_code"])) for row in rows)
    species_counts = Counter(str(row["species"]) for row in rows)

    write_csv(NORMALIZED_OUT, rows, NORMALIZED_FIELDS)
    write_csv(VALIDATION_OUT, validation_rows, VALIDATION_FIELDS)

    summary = {
        "artifact": "oil_2025_draw_results_model_target_2026_permit_totals",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(SOURCE_PDF),
        "reported_draw_year": REPORTED_DRAW_YEAR,
        "model_target_year": MODEL_TARGET_YEAR,
        "pdf_pages": len(PdfReader(str(SOURCE_PDF)).pages),
        "source_rows": len(rows),
        "unique_hunt_codes": len({row["hunt_code"] for row in rows}),
        "prefix_counts": dict(sorted(prefix_counts.items())),
        "species_counts": dict(sorted(species_counts.items())),
        "source_total_public_draw_permits": sum(int(row["total_public_draw_permits"]) for row in rows),
        "source_total_resident_draw_permits": sum(int(row["resident_total_permits"]) for row in rows),
        "source_total_nonresident_draw_permits": sum(int(row["nonresident_total_permits"]) for row in rows),
        "database_comparison_status_counts": dict(sorted(status_counts.items())),
        "database_missing_codes": status_counts.get("MISSING_DATABASE_ROW", 0),
        "database_missing_hunt_codes": [
            str(row["hunt_code"])
            for row in validation_rows
            if row["database_comparison_status"] == "MISSING_DATABASE_ROW"
        ],
        "database_match_count": status_counts.get("MATCH_DATABASE_2025_DRAW_PERMITS", 0),
        "database_difference_count": status_counts.get("DIFFERS_FROM_DATABASE_2025_DRAW_PERMITS", 0),
        "database_blank_count": status_counts.get("DATABASE_2025_DRAW_PERMITS_BLANK", 0),
        "hunt_code_mapping_status_counts": dict(
            sorted(Counter(str(row["hunt_code_mapping_status"]) for row in rows).items())
        ),
        "normalized_csv": str(NORMALIZED_OUT.relative_to(ROOT)).replace("\\", "/"),
        "validation_csv": str(VALIDATION_OUT.relative_to(ROOT)).replace("\\", "/"),
        "guardrail": "Historical draw-results evidence only; no current 2026 permit/allotment cells are modified.",
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    REPORT_OUT.write_text(build_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
