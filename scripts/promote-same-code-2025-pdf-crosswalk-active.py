from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
CROSSWALK = (
    ROOT
    / "data_truth/crosswalk_truth/validation/hunt_code_crosswalk_2024_pdf_to_2025_pdf_dropped_review.csv"
)
OUT_CSV = (
    ROOT
    / "data_truth/crosswalk_truth/validation/same_code_2025_pdf_crosswalk_active_promotions.csv"
)
SUMMARY_JSON = (
    ROOT
    / "data_truth/crosswalk_truth/validation/same_code_2025_pdf_crosswalk_active_promotions_summary.json"
)
REPORT_MD = ROOT / "processed_data/same_code_2025_pdf_crosswalk_active_promotions.md"

SOURCE_STATUS = "SAME_CODE_IN_2025_PDF_BUT_DATABASE_MARKED_HISTORICAL_ONLY_REVIEW"
ACTIVE_NOTE = "CROSSWALK_CONFIRMED_ACTIVE_SAME_CODE_IN_2025_PDF"

FIELDS = [
    "hunt_code",
    "hunt_name",
    "species",
    "weapon",
    "previous_notes",
    "new_notes",
    "previous_permit_allotment_2026_status",
    "new_permit_allotment_2026_status",
    "permits_2025_total",
    "permits_2025_draw_total",
    "permits_2026_total",
    "permit_allotment_2026_total",
]


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> int:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    db_rows, db_fields = read_csv(DATABASE)
    crosswalk_rows, _ = read_csv(CROSSWALK)
    target_codes_from_crosswalk = sorted(
        row["source_hunt_code"]
        for row in crosswalk_rows
        if row.get("crosswalk_status") == SOURCE_STATUS and row.get("mapped_hunt_code") == row.get("source_hunt_code")
    )
    db_by_code = {row["hunt_code"]: row for row in db_rows}
    already_promoted_codes = sorted(
        row["hunt_code"]
        for row in db_rows
        if row.get("NOTES") == ACTIVE_NOTE
        and row.get("permit_allotment_2026_status")
        == "CROSSWALK_CONFIRMED_ACTIVE_2025_PDF_2026_NUMBERS_PENDING"
    )
    target_codes = sorted(set(target_codes_from_crosswalk) | set(already_promoted_codes))

    changed: list[dict[str, Any]] = []
    missing_codes = [code for code in target_codes if code not in db_by_code]
    if missing_codes:
        raise RuntimeError(f"Target codes missing from DATABASE.csv: {missing_codes}")

    for code in target_codes:
        row = db_by_code[code]
        previous_notes = row.get("NOTES", "")
        previous_status = row.get("permit_allotment_2026_status", "")
        row["NOTES"] = ACTIVE_NOTE
        row["permit_allotment_2026_status"] = "CROSSWALK_CONFIRMED_ACTIVE_2025_PDF_2026_NUMBERS_PENDING"
        changed.append(
            {
                "hunt_code": code,
                "hunt_name": row.get("hunt_name", ""),
                "species": row.get("species", ""),
                "weapon": row.get("weapon", ""),
                "previous_notes": previous_notes,
                "new_notes": row["NOTES"],
                "previous_permit_allotment_2026_status": previous_status,
                "new_permit_allotment_2026_status": row["permit_allotment_2026_status"],
                "permits_2025_total": row.get("permits_2025_total", ""),
                "permits_2025_draw_total": row.get("permits_2025_draw_total", ""),
                "permits_2026_total": row.get("permits_2026_total", ""),
                "permit_allotment_2026_total": row.get("permit_allotment_2026_total", ""),
            }
        )

    write_csv(DATABASE, db_rows, db_fields)
    write_csv(OUT_CSV, changed, FIELDS)

    summary = {
        "artifact": "same_code_2025_pdf_crosswalk_active_promotions",
        "generated_at_utc": generated_at,
        "database_csv": DATABASE.relative_to(ROOT).as_posix(),
        "crosswalk_csv": CROSSWALK.relative_to(ROOT).as_posix(),
        "guardrail": "Reclassifies same-code/name-matched 2025 PDF rows as active crosswalk rows. Does not populate or alter 2026 permit/allotment numbers.",
        "target_code_count": len(target_codes),
        "target_codes_from_crosswalk_count": len(target_codes_from_crosswalk),
        "already_promoted_code_count": len(already_promoted_codes),
        "target_codes": target_codes,
        "changed_row_count": len(changed),
        "changed_codes": [row["hunt_code"] for row in changed],
        "outputs": {
            "promotion_csv": OUT_CSV.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "report_md": REPORT_MD.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Same-Code 2025 PDF Crosswalk Active Promotions",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Reclassified rows: `{len(changed)}`",
        "- No 2026 permit/allotment numbers were populated or changed.",
        "",
        "| Hunt code | Hunt name | Species | 2025 total | 2026 total | New status |",
        "|---|---|---|---:|---:|---|",
    ]
    for row in changed:
        lines.append(
            f"| {row['hunt_code']} | {row['hunt_name']} | {row['species']} | "
            f"{row['permits_2025_total']} | {row['permits_2026_total']} | {row['new_permit_allotment_2026_status']} |"
        )
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
