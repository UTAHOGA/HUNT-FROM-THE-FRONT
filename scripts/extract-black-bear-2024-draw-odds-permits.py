"""Extract 2024 black bear draw-odds permit totals.

The source PDF is a completed draw-results file. Per project year rules, the
reported draw/hunt year is 2024 and the model target year is 2025.
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


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2025/pdf/draw_odds/24 bear draw odds complete.pdf"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"

REPORTED_DRAW_YEAR = 2024
MODEL_TARGET_YEAR = 2025

NORMALIZED_OUT = ROOT / "data_truth/draw_results_truth/normalized/black_bear_2024_draw_odds_model_target_2025_permit_totals.csv"
VALIDATION_OUT = ROOT / "data_truth/draw_results_truth/validation/black_bear_2024_draw_odds_model_target_2025_vs_DATABASE.csv"
SUMMARY_OUT = ROOT / "data_truth/draw_results_truth/validation/black_bear_2024_draw_odds_model_target_2025_summary.json"
REPORT_OUT = ROOT / "processed_data/black_bear_2024_draw_odds_model_target_2025_permit_totals.md"

NORMALIZED_FIELDS = [
    "hunt_code",
    "hunt_name",
    "raw_hunt_name",
    "reported_draw_year",
    "model_target_year",
    "source_file",
    "source_sha256",
    "page_number",
    "resident_eligible_applicants",
    "resident_bonus_permits",
    "resident_regular_permits",
    "resident_total_permits",
    "nonresident_eligible_applicants",
    "nonresident_bonus_permits",
    "nonresident_regular_permits",
    "nonresident_total_permits",
    "total_public_permits",
    "source_classification",
]

VALIDATION_FIELDS = NORMALIZED_FIELDS + [
    "database_hunt_name",
    "database_species",
    "database_weapon",
    "database_hunt_type",
    "database_permits_2025_res",
    "database_permits_2025_nr",
    "database_permits_2025_total",
    "database_permits_2025_source",
    "database_permits_2026_total",
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


def parse_pdf() -> list[dict[str, object]]:
    try:
        import pdfplumber
    except Exception as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("pdfplumber is required to extract the bear draw-odds PDF.") from exc

    rows: list[dict[str, object]] = []
    source_hash = sha256(SOURCE_PDF)
    source_rel = str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/")
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            hunt_match = re.search(r"Hunt:\s*(BR\d{4})\s+(.+?)\nResident Applicants", text, re.S)
            if not hunt_match:
                continue
            totals = re.findall(r"Totals\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", text)
            if len(totals) < 2:
                raise RuntimeError(f"Could not extract resident/nonresident totals on page {page_number}")

            raw_name = " ".join(hunt_match.group(2).split()).strip()
            hunt_name = re.sub(r"\s+-\s+.*$", "", raw_name).strip()
            resident = tuple(int(value) for value in totals[0])
            nonresident = tuple(int(value) for value in totals[1])
            rows.append(
                {
                    "hunt_code": hunt_match.group(1).strip().upper(),
                    "hunt_name": hunt_name,
                    "raw_hunt_name": raw_name,
                    "reported_draw_year": REPORTED_DRAW_YEAR,
                    "model_target_year": MODEL_TARGET_YEAR,
                    "source_file": source_rel,
                    "source_sha256": source_hash,
                    "page_number": page_number,
                    "resident_eligible_applicants": resident[0],
                    "resident_bonus_permits": resident[1],
                    "resident_regular_permits": resident[2],
                    "resident_total_permits": resident[3],
                    "nonresident_eligible_applicants": nonresident[0],
                    "nonresident_bonus_permits": nonresident[1],
                    "nonresident_regular_permits": nonresident[2],
                    "nonresident_total_permits": nonresident[3],
                    "total_public_permits": resident[3] + nonresident[3],
                    "source_classification": "BEAR_PURSUIT_BONUS_DRAW" if "pursuit" in raw_name.lower() else "TRUE_BEAR_BONUS_DRAW",
                }
            )
    return rows


def load_database() -> dict[str, dict[str, str]]:
    rows, _ = read_csv(DATABASE)
    return {row.get("hunt_code", "").upper(): row for row in rows}


def compare_database(rows: list[dict[str, object]], db_by_code: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in rows:
        code = str(row["hunt_code"])
        db = db_by_code.get(code, {})
        db_res = db.get("permits_2025_res", "")
        db_nr = db.get("permits_2025_nr", "")
        db_total = db.get("permits_2025_total", "")
        source_res = str(row["resident_total_permits"])
        source_nr = str(row["nonresident_total_permits"])
        source_total = str(row["total_public_permits"])

        if not db:
            status = "MISSING_DATABASE_ROW"
            note = "Draw-odds hunt code does not exist in current DATABASE.csv."
        elif (db_res, db_nr, db_total) == (source_res, source_nr, source_total):
            status = "MATCH_DATABASE_2025_PERMITS"
            note = "Source totals match DATABASE.csv 2025 permit fields."
        elif not (db_res or db_nr or db_total):
            status = "DATABASE_2025_PERMITS_BLANK"
            note = "Draw-odds source has historical totals; DATABASE.csv has no populated 2025 permit fields."
        else:
            status = "DIFFERS_FROM_DATABASE_2025_PERMITS"
            note = "Do not overwrite automatically; draw-odds reported year and DATABASE 2025 lineage must be reviewed."

        output.append(
            {
                **row,
                "database_hunt_name": db.get("hunt_name", ""),
                "database_species": db.get("species", ""),
                "database_weapon": db.get("weapon", ""),
                "database_hunt_type": db.get("hunt_type", ""),
                "database_permits_2025_res": db_res,
                "database_permits_2025_nr": db_nr,
                "database_permits_2025_total": db_total,
                "database_permits_2025_source": db.get("permits_2025_source", ""),
                "database_permits_2026_total": db.get("permits_2026_total", ""),
                "database_comparison_status": status,
                "review_note": note,
            }
        )
    return output


def build_report(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Black Bear 2024 Draw-Odds Permit Totals",
            "",
            f"- Source PDF: `{summary['source_file']}`",
            f"- Reported draw year: `{summary['reported_draw_year']}`",
            f"- Model target year: `{summary['model_target_year']}`",
            f"- Hunt-code rows extracted: `{summary['source_rows']}`",
            f"- Total public permits in source: `{summary['source_total_public_permits']}`",
            f"- DATABASE missing codes: `{summary['database_missing_codes']}`",
            f"- DATABASE 2025 permit matches: `{summary['database_match_count']}`",
            f"- DATABASE 2025 permit differences requiring review: `{summary['database_difference_count']}`",
            "",
            "This is a historical draw-results source. It is not promoted into 2026 current availability fields.",
            "",
        ]
    )


def main() -> None:
    rows = parse_pdf()
    if len(rows) != len({row["hunt_code"] for row in rows}):
        raise RuntimeError("Duplicate BR hunt codes found in draw-odds extraction")
    db_by_code = load_database()
    validation_rows = compare_database(rows, db_by_code)
    status_counts = Counter(str(row["database_comparison_status"]) for row in validation_rows)
    classification_counts = Counter(str(row["source_classification"]) for row in rows)

    write_csv(NORMALIZED_OUT, rows, NORMALIZED_FIELDS)
    write_csv(VALIDATION_OUT, validation_rows, VALIDATION_FIELDS)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(SOURCE_PDF),
        "reported_draw_year": REPORTED_DRAW_YEAR,
        "model_target_year": MODEL_TARGET_YEAR,
        "source_rows": len(rows),
        "unique_hunt_codes": len({row["hunt_code"] for row in rows}),
        "source_total_public_permits": sum(int(row["total_public_permits"]) for row in rows),
        "source_total_resident_permits": sum(int(row["resident_total_permits"]) for row in rows),
        "source_total_nonresident_permits": sum(int(row["nonresident_total_permits"]) for row in rows),
        "source_classification_counts": dict(classification_counts),
        "database_comparison_status_counts": dict(status_counts),
        "database_missing_codes": status_counts.get("MISSING_DATABASE_ROW", 0),
        "database_match_count": status_counts.get("MATCH_DATABASE_2025_PERMITS", 0),
        "database_difference_count": status_counts.get("DIFFERS_FROM_DATABASE_2025_PERMITS", 0),
        "database_blank_count": status_counts.get("DATABASE_2025_PERMITS_BLANK", 0),
        "normalized_csv": str(NORMALIZED_OUT.relative_to(ROOT)).replace("\\", "/"),
        "validation_csv": str(VALIDATION_OUT.relative_to(ROOT)).replace("\\", "/"),
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    REPORT_OUT.write_text(build_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
