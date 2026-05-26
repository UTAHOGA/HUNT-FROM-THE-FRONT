from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATABASE_CSV = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
SOURCE_AUDIT_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits.csv"
)
BEAR_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2025/pdf/draw_odds/Bear/2024 Bear Draw Results.pdf"

PROMOTION_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "source_only_br_2024_draw_pdf_values_promoted_to_DATABASE_2025.csv"
)
SUMMARY_JSON = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "source_only_br_2024_draw_pdf_values_promoted_to_DATABASE_2025_summary.json"
)
REPORT_MD = ROOT / "processed_data/source_only_br_2024_draw_pdf_values_promoted_to_DATABASE_2025.md"

SOURCE_LABEL = "2024_BEAR_DRAW_RESULTS_PDF_MODEL_TARGET_2025"
TARGET_CODES = {"BR7008", "BR7019", "BR7108", "BR7208"}

CODE_METADATA = {
    "BR7008": {
        "boundary_id": "684",
        "hunt_name": "La Sal",
        "hunt_type": "Limited Entry - Spring",
        "season": "Historical 2025 draw only; season dates not validated in current DATABASE",
    },
    "BR7019": {
        "boundary_id": "610",
        "hunt_name": "Chalk Creek/East Canyon/Morgan-South Rich",
        "hunt_type": "Limited Entry - Spring",
        "season": "Historical 2025 draw only; season dates not validated in current DATABASE",
    },
    "BR7108": {
        "boundary_id": "684",
        "hunt_name": "La Sal",
        "hunt_type": "Limited Entry - Summer",
        "season": "Historical 2025 draw only; season dates not validated in current DATABASE",
    },
    "BR7208": {
        "boundary_id": "684",
        "hunt_name": "La Sal",
        "hunt_type": "Limited Entry - Fall",
        "season": "Historical 2025 draw only; season dates not validated in current DATABASE",
    },
}


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field, "") for field in fieldnames})


def clean_int(value: str) -> str:
    return str(int(str(value).strip()))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_database_row(source: dict[str, str], fields: list[str]) -> dict[str, str]:
    code = source["hunt_code"].strip()
    meta = CODE_METADATA[code]
    res = clean_int(source["resident_total_permits"])
    nr = clean_int(source["nonresident_total_permits"])
    total = clean_int(source["total_public_draw_permits"])

    row = {field: "" for field in fields}
    row.update(
        {
            "hunt_code": code,
            "boundary_id": meta["boundary_id"],
            "hunt_name": meta["hunt_name"],
            "sex_type": "Either Sex",
            "species": "Black Bear",
            "weapon": "Any Legal Weapon",
            "hunt_type": meta["hunt_type"],
            "season": meta["season"],
            "NOTES": "HISTORICAL_2025_DRAW_ONLY_NOT_ACTIVE_2026",
            "permits_2025_draw_res": res,
            "permits_2025_draw_nr": nr,
            "permits_2025_draw_total": total,
            "draw_2025_bg_pdf_page": source["source_page"].strip(),
            "draw_2025_type": "2024 Bear Draw Results PDF Model Target 2025",
            "permits_2025_draw_source": SOURCE_LABEL,
            "permits_2025_res": res,
            "permits_2025_nr": nr,
            "permits_2025_total": total,
            "permits_2025_source": SOURCE_LABEL,
            "permit_allotment_2026_status": "HISTORICAL_2025_ONLY_NOT_ACTIVE_2026",
        }
    )
    return row


def main() -> int:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if not BEAR_PDF.exists():
        raise FileNotFoundError(f"Missing source PDF: {BEAR_PDF}")

    db_rows, db_fields = read_csv(DATABASE_CSV)
    existing_codes = {row["hunt_code"].strip() for row in db_rows}
    source_rows, _ = read_csv(SOURCE_AUDIT_CSV)
    source_by_code = {row["hunt_code"].strip(): row for row in source_rows}

    missing_source_codes = sorted(TARGET_CODES - set(source_by_code))
    if missing_source_codes:
        raise RuntimeError(f"Source audit missing target codes: {missing_source_codes}")

    inserted_rows: list[dict[str, Any]] = []
    skipped_existing: list[str] = []
    for code in sorted(TARGET_CODES):
        if code in existing_codes:
            skipped_existing.append(code)
            continue
        source = source_by_code[code]
        db_row = make_database_row(source, db_fields)
        db_rows.append(db_row)
        inserted_rows.append(
            {
                "hunt_code": code,
                "boundary_id": db_row["boundary_id"],
                "hunt_name": db_row["hunt_name"],
                "hunt_type": db_row["hunt_type"],
                "source_hunt_name": source["hunt_name"],
                "source_file": source["source_file"],
                "source_page": source["source_page"],
                "source_resident_permits": source["resident_total_permits"],
                "source_nonresident_permits": source["nonresident_total_permits"],
                "source_total_permits": source["total_public_draw_permits"],
                "permits_2025_source": SOURCE_LABEL,
                "notes": db_row["NOTES"],
            }
        )

    write_csv(DATABASE_CSV, db_rows, db_fields)

    promotion_fields = [
        "hunt_code",
        "boundary_id",
        "hunt_name",
        "hunt_type",
        "source_hunt_name",
        "source_file",
        "source_page",
        "source_resident_permits",
        "source_nonresident_permits",
        "source_total_permits",
        "permits_2025_source",
        "notes",
    ]
    write_csv(PROMOTION_CSV, inserted_rows, promotion_fields)

    summary = {
        "artifact": "source_only_br_2024_draw_pdf_values_promoted_to_DATABASE_2025",
        "generated_at_utc": generated_at,
        "database_csv": DATABASE_CSV.relative_to(ROOT).as_posix(),
        "source_audit_csv": SOURCE_AUDIT_CSV.relative_to(ROOT).as_posix(),
        "source_pdf": BEAR_PDF.relative_to(ROOT).as_posix(),
        "source_pdf_sha256": sha256_file(BEAR_PDF),
        "source_label": SOURCE_LABEL,
        "guardrail": "Promotes only user-confirmed 2025 historical draw rows. All 2026 permit/allotment fields remain blank.",
        "target_codes": sorted(TARGET_CODES),
        "inserted_row_count": len(inserted_rows),
        "inserted_codes": [row["hunt_code"] for row in inserted_rows],
        "skipped_existing_count": len(skipped_existing),
        "skipped_existing_codes": skipped_existing,
        "outputs": {
            "promotion_csv": PROMOTION_CSV.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "report_md": REPORT_MD.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Source-Only BR 2024 Draw PDF Values Promoted To DATABASE 2025",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Inserted historical 2025 rows: `{len(inserted_rows)}`",
        f"- Source PDF SHA256: `{summary['source_pdf_sha256']}`",
        "",
        "These rows are historical 2025 draw-result rows only. No 2026 permit/allotment values were populated.",
        "",
        "| Hunt code | Boundary ID | Hunt name | Hunt type | Res | Nonres | Total | Source page |",
        "|---|---:|---|---|---:|---:|---:|---:|",
    ]
    for row in inserted_rows:
        lines.append(
            "| {hunt_code} | {boundary_id} | {hunt_name} | {hunt_type} | "
            "{source_resident_permits} | {source_nonresident_permits} | {source_total_permits} | {source_page} |".format(
                **row
            )
        )
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
