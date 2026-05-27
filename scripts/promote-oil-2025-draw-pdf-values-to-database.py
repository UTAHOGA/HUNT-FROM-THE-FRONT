from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATABASE_CSV = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
OIL_VALIDATION_CSV = (
    ROOT / "data_truth/draw_results_truth/validation/oil_2025_draw_results_model_target_2026_vs_DATABASE.csv"
)
OUT_CSV = (
    ROOT / "data_truth/draw_results_truth/validation/oil_2025_draw_pdf_values_promoted_to_DATABASE.csv"
)
SUMMARY_JSON = (
    ROOT / "data_truth/draw_results_truth/validation/oil_2025_draw_pdf_values_promoted_to_DATABASE_summary.json"
)
REPORT_MD = ROOT / "processed_data/oil_2025_draw_pdf_values_promoted_to_DATABASE.md"

SOURCE_LABEL = "2025_OIL_DRAW_RESULTS_PDF_MODEL_TARGET_2026"
DRAW_TYPE = "2025 O.I.L. Draw Results PDF Model Target 2026"
ACTIVE_PENDING_STATUS = "CROSSWALK_CONFIRMED_ACTIVE_2025_OIL_PDF_2026_NUMBERS_PENDING"
ACTIVE_CWMU_NOTE = "OIL_2025_PDF_AND_HARVEST_CONFIRMED_ACTIVE_CWMU_REVIEWED"

MISSING_CODE_METADATA = {
    "MB6225": {
        "boundary_id": "586",
        "hunt_name": "Wallsburg CWMU",
        "sex_type": "Bull",
        "species": "Moose",
        "weapon": "Any Legal Weapon",
        "hunt_type": "CWMU",
        "season": "Contact operator for season dates",
    },
    "MB6257": {
        "boundary_id": "493",
        "hunt_name": "Ingham Peak CWMU",
        "sex_type": "Bull",
        "species": "Moose",
        "weapon": "Any Legal Weapon",
        "hunt_type": "CWMU",
        "season": "Contact operator for season dates",
    },
}

PROMOTION_FIELDS = [
    "hunt_code",
    "action",
    "boundary_id",
    "hunt_name",
    "species",
    "sex_type",
    "weapon",
    "hunt_type",
    "previous_permits_2025_draw_res",
    "previous_permits_2025_draw_nr",
    "previous_permits_2025_draw_total",
    "new_permits_2025_draw_res",
    "new_permits_2025_draw_nr",
    "new_permits_2025_draw_total",
    "previous_permits_2025_draw_source",
    "new_permits_2025_draw_source",
    "source_file",
    "source_sha256",
    "pdf_page_number",
    "source_report_page",
    "note",
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
            writer.writerow({field: "" if row.get(field) is None else row.get(field, "") for field in fields})


def int_text(value: str) -> str:
    return str(int(str(value).replace(",", "").strip()))


def apply_2025_draw_values(db_row: dict[str, str], source: dict[str, str]) -> dict[str, str]:
    res = int_text(source["resident_total_permits"])
    nr = int_text(source["nonresident_total_permits"])
    total = int_text(source["total_public_draw_permits"])

    db_row["permits_2025_draw_res"] = res
    db_row["permits_2025_draw_nr"] = nr
    db_row["permits_2025_draw_total"] = total
    db_row["draw_2025_bg_pdf_page"] = source["pdf_page_number"]
    db_row["draw_2025_bg_report_page"] = source["source_report_page"]
    db_row["draw_2025_type"] = DRAW_TYPE
    db_row["permits_2025_draw_source"] = SOURCE_LABEL
    db_row["permits_2025_res"] = res
    db_row["permits_2025_nr"] = nr
    db_row["permits_2025_total"] = total
    db_row["permits_2025_source"] = SOURCE_LABEL
    return {"res": res, "nr": nr, "total": total}


def make_missing_database_row(source: dict[str, str], fields: list[str]) -> dict[str, str]:
    code = source["hunt_code"]
    meta = MISSING_CODE_METADATA[code]
    row = {field: "" for field in fields}
    row.update(
        {
            "hunt_code": code,
            "boundary_id": meta["boundary_id"],
            "hunt_name": meta["hunt_name"],
            "sex_type": meta["sex_type"],
            "species": meta["species"],
            "weapon": meta["weapon"],
            "hunt_type": meta["hunt_type"],
            "season": meta["season"],
            "NOTES": ACTIVE_CWMU_NOTE,
            "permit_allotment_2026_status": ACTIVE_PENDING_STATUS,
        }
    )
    apply_2025_draw_values(row, source)
    return row


def main() -> int:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    db_rows, db_fields = read_csv(DATABASE_CSV)
    validation_rows, _ = read_csv(OIL_VALIDATION_CSV)
    db_by_code = {row["hunt_code"]: row for row in db_rows}

    target_rows = [
        row
        for row in validation_rows
        if row.get("database_comparison_status")
        in {"DIFFERS_FROM_DATABASE_2025_DRAW_PERMITS", "MISSING_DATABASE_ROW"}
    ]
    if not target_rows:
        target_rows = [
            row
            for row in validation_rows
            if row.get("hunt_code") in MISSING_CODE_METADATA
            or row.get("permits_2025_draw_source") == SOURCE_LABEL
        ]

    promoted: list[dict[str, Any]] = []
    inserted_codes: list[str] = []
    updated_codes: list[str] = []

    for source in target_rows:
        code = source["hunt_code"]
        previous = db_by_code.get(code)
        action = "UPDATED_EXISTING_ROW" if previous else "INSERTED_REVIEWED_CWMU_ROW"
        if previous:
            db_row = previous
        else:
            if code not in MISSING_CODE_METADATA:
                raise RuntimeError(f"No reviewed metadata exists for missing O.I.L. code {code}")
            db_row = make_missing_database_row(source, db_fields)
            db_rows.append(db_row)
            db_by_code[code] = db_row
            inserted_codes.append(code)

        prev_res = previous.get("permits_2025_draw_res", "") if previous else ""
        prev_nr = previous.get("permits_2025_draw_nr", "") if previous else ""
        prev_total = previous.get("permits_2025_draw_total", "") if previous else ""
        prev_source = previous.get("permits_2025_draw_source", "") if previous else ""
        new_values = apply_2025_draw_values(db_row, source)
        if previous:
            updated_codes.append(code)

        promoted.append(
            {
                "hunt_code": code,
                "action": action,
                "boundary_id": db_row.get("boundary_id", ""),
                "hunt_name": db_row.get("hunt_name", ""),
                "species": db_row.get("species", ""),
                "sex_type": db_row.get("sex_type", ""),
                "weapon": db_row.get("weapon", ""),
                "hunt_type": db_row.get("hunt_type", ""),
                "previous_permits_2025_draw_res": prev_res,
                "previous_permits_2025_draw_nr": prev_nr,
                "previous_permits_2025_draw_total": prev_total,
                "new_permits_2025_draw_res": new_values["res"],
                "new_permits_2025_draw_nr": new_values["nr"],
                "new_permits_2025_draw_total": new_values["total"],
                "previous_permits_2025_draw_source": prev_source,
                "new_permits_2025_draw_source": SOURCE_LABEL,
                "source_file": source.get("source_file", ""),
                "source_sha256": source.get("source_sha256", ""),
                "pdf_page_number": source.get("pdf_page_number", ""),
                "source_report_page": source.get("source_report_page", ""),
                "note": "Promoted reviewed 2025 O.I.L. PDF draw-results values; 2026 permit/allotment values were not changed.",
            }
        )

    codes = [row["hunt_code"] for row in db_rows]
    duplicates = sorted(code for code in set(codes) if codes.count(code) > 1)
    if duplicates:
        raise RuntimeError(f"Duplicate hunt codes after O.I.L. promotion: {duplicates}")

    write_csv(DATABASE_CSV, db_rows, db_fields)
    write_csv(OUT_CSV, promoted, PROMOTION_FIELDS)

    summary = {
        "artifact": "oil_2025_draw_pdf_values_promoted_to_DATABASE",
        "generated_at_utc": generated_at,
        "database_csv": DATABASE_CSV.relative_to(ROOT).as_posix(),
        "source_validation_csv": OIL_VALIDATION_CSV.relative_to(ROOT).as_posix(),
        "source_label": SOURCE_LABEL,
        "guardrail": "Promotes reviewed 2025 O.I.L. PDF draw-results values only. Does not populate or overwrite 2026 live permit/allotment fields.",
        "promoted_row_count": len(promoted),
        "updated_existing_row_count": len(updated_codes),
        "inserted_row_count": len(inserted_codes),
        "updated_existing_codes": updated_codes,
        "inserted_codes": inserted_codes,
        "outputs": {
            "promotion_csv": OUT_CSV.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "report_md": REPORT_MD.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# 2025 O.I.L. PDF Values Promoted To DATABASE",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Existing rows updated: `{len(updated_codes)}`",
        f"- Reviewed CWMU rows inserted: `{len(inserted_codes)}`",
        "- No 2026 permit/allotment values were populated or changed.",
        "",
        "| Hunt code | Action | Boundary ID | Hunt name | Species | Res | Nonres | Total | Source report page |",
        "|---|---|---:|---|---|---:|---:|---:|---:|",
    ]
    for row in promoted:
        lines.append(
            "| {hunt_code} | {action} | {boundary_id} | {hunt_name} | {species} | "
            "{new_permits_2025_draw_res} | {new_permits_2025_draw_nr} | {new_permits_2025_draw_total} | "
            "{source_report_page} |".format(**row)
        )
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
