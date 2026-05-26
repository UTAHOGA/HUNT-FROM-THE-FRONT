from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CONSERVATION_CYCLE = ROOT / "data_truth/permit_overlay_truth/normalized/conservation_permit_cycle_rows_2022_2027.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
BLACK_BEAR_SOURCE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 black bear permits.csv"

LOCK_CSV = ROOT / "data_truth/permit_overlay_truth/normalized/black_bear_conservation_BR7307_lock_2026.csv"
AUDIT_CSV = ROOT / "data_truth/permit_overlay_truth/validation/black_bear_conservation_BR7307_lock_2026_audit.csv"
SUMMARY_JSON = ROOT / "processed_data/black_bear_conservation_BR7307_lock_2026_summary.json"
REPORT_MD = ROOT / "processed_data/black_bear_conservation_BR7307_lock_2026.md"

SOURCE_AUTHORITY = "Utah DWR 2025-2027 Conservation Permit Database"
SOURCE_FILE = "conservation-permit-hunt-table-2025-27.csv"
DATA_CUTOFF_DATE = "2026-05-26"

LOCK = {
    "hunt_code": "BR7307",
    "hunt_name": "La Sal",
    "species": "Black Bear",
    "sex_type": "Either Sex",
    "weapon": "Multiseason",
    "hunt_type": "Multiseason - Conservation",
    "season": "Mar. 28 - May 25 & May 25 - June 28 & Aug. 1 - Aug. 31 & Nov 2 - Nov. 8, 2026",
    "res": "",
    "non_res": "",
    "total": "4",
    "permit_status": "TOTAL_ONLY",
    "permit_allocation_type": "CONSERVATION_MULTIYEAR_SUMMED_TOTAL",
    "permit_source_authority": SOURCE_AUTHORITY,
    "permit_overlay_source": SOURCE_FILE,
    "data_status": "COMPLETE_TOTAL_ONLY",
    "model_version": "black_bear_conservation_reference_v1.0.0",
    "rule_version": "utah_black_bear_conservation_code_lock_v1.0.0",
}

PDF_EVIDENCE_ROWS = [
    {"source_page_or_row": "36", "organization": "UHA", "group": "UHA", "permit_count": "1"},
    {"source_page_or_row": "37", "organization": "SFW", "group": "SFW", "permit_count": "1"},
    {"source_page_or_row": "38", "organization": "MDF", "group": "MDF", "permit_count": "1"},
    {"source_page_or_row": "39", "organization": "SFW", "group": "SFW", "permit_count": "1"},
]

TARGET_FILES = [
    "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
    "processed_data/hunt_master_enriched.csv",
    "processed_data/draw_reality_engine.csv",
    "processed_data/point_ladder_view.csv",
    "processed_data/draw_reality_engine_predictive_v2.csv",
    "processed_data/bear_draw_predictions_v1.csv",
    "processed_data/bear_predictions_v1.csv",
    "data_model/runtime_drafts/point_ladder_view_v2.csv",
    "data_model/runtime_drafts/mixed_predictive_engine_2026.materialized.csv",
    "data_model/runtime_drafts/mixed_predictive_engine_2026.predictions.csv",
    "data_model/harvest_quality/draw_reality_engine_predictive_with_harvest_features.csv",
    "data_model/harvest_quality/ml_draw_predictions_with_harvest_features.csv",
    "data_model/validation/hunt_master_enriched_duplicate_audit.csv",
    "data_truth/regulations_truth/normalized/2026_bear_cougar_furbearer_guidebook_bear_hunt_code_reconciliation.csv",
]

LOCK_FIELDS = [
    "hunt_code",
    "hunt_name",
    "species",
    "sex_type",
    "weapon",
    "hunt_type",
    "season",
    "Non Res",
    "Res",
    "Total",
    "permit_status",
    "permit_allocation_type",
    "permit_source_authority",
    "permit_overlay_source",
    "data_status",
    "model_version",
    "rule_version",
    "source_row_id",
    "source_row_count",
    "source_rows_total_if_summed",
    "source_page_or_row",
    "note",
]

AUDIT_FIELDS = [
    "file",
    "row_number",
    "hunt_code",
    "field",
    "old_value",
    "new_value",
    "audit_status",
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip().replace("\ufeff", "")


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]], str, str]:
    raw = path.read_bytes()
    encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    newline = "\r\n" if b"\r\n" in raw[:8192] else "\n"
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [{key: clean(value) for key, value in row.items()} for row in reader]
        return list(reader.fieldnames or []), rows, encoding, newline


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]], encoding: str = "utf-8", newline: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator=newline)
        writer.writeheader()
        writer.writerows(rows)


def note(source_rows: list[dict[str, str]]) -> str:
    orgs = ", ".join(
        f"{row['organization']} row {row['source_page_or_row']}"
        for row in source_rows
        if row.get("organization")
    )
    return (
        "Current DWR Hunt Planner row confirms BR7307 as La Sal black bear multiseason conservation. "
        "Locked as the summed total-only conservation hunt-code reference across the organization rows; "
        f"resident/nonresident split is not published. Conservation cycle evidence rows under the same source row ID include: {orgs}."
    )


def validate_sources() -> tuple[dict[str, str], list[dict[str, str]], list[str]]:
    errors: list[str] = []
    _, bear_rows, _, _ = read_rows(BLACK_BEAR_SOURCE)
    bear_match = next((row for row in bear_rows if row.get("hunt_code") == LOCK["hunt_code"]), None)
    if not bear_match:
        errors.append("BR7307 missing from current 2026 black bear permit source.")
        bear_match = {}
    else:
        if bear_match.get("hunt_name") != LOCK["hunt_name"]:
            errors.append(f"BR7307 source hunt_name mismatch: {bear_match.get('hunt_name')!r}")
        if bear_match.get("weapon ") != LOCK["weapon"] and bear_match.get("weapon") != LOCK["weapon"]:
            errors.append(f"BR7307 source weapon mismatch: {bear_match.get('weapon ') or bear_match.get('weapon')!r}")
        if bear_match.get("hunt_type") != LOCK["hunt_type"]:
            errors.append(f"BR7307 source hunt_type mismatch: {bear_match.get('hunt_type')!r}")
        if "Nov 2 - Nov. 8, 2026" not in bear_match.get("season", ""):
            errors.append("BR7307 source season does not match expected multiseason conservation season.")

    _, conservation_rows, _, _ = read_rows(CONSERVATION_CYCLE)
    source_rows = [
        row
        for row in conservation_rows
        if row.get("cycle") == "2025-2027"
        and row.get("source_file") == SOURCE_FILE
        and row.get("source_row_id") == "CP-BLACK-BEAR-LA-SAL-EITHER-SEX-MULTISEASON"
        and row.get("species_family") == "Black Bear"
        and row.get("area") == "La Sal"
        and row.get("discontinued_flag") == "False"
    ]
    if not source_rows:
        errors.append("Missing 2025-2027 conservation permit source rows for La Sal black bear multiseason.")
    elif sum(int(float(row.get("permit_count", "0") or 0)) for row in source_rows) != int(LOCK["total"]):
        errors.append("Conservation source rows do not sum to the locked BR7307 total.")
    return bear_match, source_rows, errors


def lock_output_row(source_rows: list[dict[str, str]]) -> dict[str, str]:
    total_if_summed = sum(int(float(row.get("permit_count", "0") or 0)) for row in PDF_EVIDENCE_ROWS)
    pages = "|".join(row["source_page_or_row"] for row in PDF_EVIDENCE_ROWS)
    row = {
        **LOCK,
        "Non Res": LOCK["non_res"],
        "Res": LOCK["res"],
        "Total": LOCK["total"],
        "source_row_id": "CP-BLACK-BEAR-LA-SAL-EITHER-SEX-MULTISEASON",
        "source_row_count": str(len(PDF_EVIDENCE_ROWS)),
        "source_rows_total_if_summed": str(total_if_summed),
        "source_page_or_row": pages,
        "note": note(PDF_EVIDENCE_ROWS),
    }
    return row


def set_if_present(
    row: dict[str, str],
    field: str,
    value: str,
    audit: list[dict[str, str]],
    file_name: str,
    row_number: int,
) -> None:
    if field not in row:
        return
    old_value = clean(row.get(field))
    if old_value == value:
        return
    row[field] = value
    audit.append(
        {
            "file": file_name,
            "row_number": str(row_number),
            "hunt_code": LOCK["hunt_code"],
            "field": field,
            "old_value": old_value,
            "new_value": value,
            "audit_status": "CHANGED",
        }
    )


def apply_updates(row: dict[str, str], audit: list[dict[str, str]], file_name: str, row_number: int, source_note: str) -> None:
    set_if_present(row, "hunt_name", LOCK["hunt_name"], audit, file_name, row_number)
    set_if_present(row, "species", LOCK["species"], audit, file_name, row_number)
    set_if_present(row, "sex_type", LOCK["sex_type"], audit, file_name, row_number)
    set_if_present(row, "weapon", LOCK["weapon"], audit, file_name, row_number)
    set_if_present(row, "hunt_type", LOCK["hunt_type"], audit, file_name, row_number)
    set_if_present(row, "season", LOCK["season"], audit, file_name, row_number)
    set_if_present(row, "season_dates", LOCK["season"], audit, file_name, row_number)

    for field in ("permits_2026_total", "permit_allotment_2026_total", "public_permits_2026", "quota_2026_total"):
        set_if_present(row, field, LOCK["total"], audit, file_name, row_number)

    for field in ("permits_2026_res", "permit_allotment_2026_res"):
        set_if_present(row, field, LOCK["res"], audit, file_name, row_number)
    for field in ("permits_2026_nr", "permit_allotment_2026_nr"):
        set_if_present(row, field, LOCK["non_res"], audit, file_name, row_number)

    set_if_present(row, "permit_status", LOCK["permit_status"], audit, file_name, row_number)
    set_if_present(row, "permit_allocation_type", LOCK["permit_allocation_type"], audit, file_name, row_number)
    set_if_present(row, "permit_source_authority", LOCK["permit_source_authority"], audit, file_name, row_number)
    set_if_present(row, "permit_note", source_note, audit, file_name, row_number)
    set_if_present(row, "permit_overlay_source", LOCK["permit_overlay_source"], audit, file_name, row_number)
    set_if_present(row, "data_status", LOCK["data_status"], audit, file_name, row_number)
    set_if_present(row, "permit_allotment_2026_status", LOCK["permit_status"], audit, file_name, row_number)
    set_if_present(row, "permit_allotment_2026_source", LOCK["permit_source_authority"], audit, file_name, row_number)
    set_if_present(row, "permit_allotment_2026_source_file", LOCK["permit_overlay_source"], audit, file_name, row_number)
    set_if_present(row, "public_permits_2026_source", LOCK["permit_source_authority"], audit, file_name, row_number)
    set_if_present(row, "permits_2026_source", LOCK["permit_source_authority"], audit, file_name, row_number)
    set_if_present(row, "quota_source", LOCK["permit_source_authority"], audit, file_name, row_number)
    set_if_present(row, "quota_source_status", LOCK["permit_status"], audit, file_name, row_number)
    set_if_present(row, "quota_source_file", LOCK["permit_overlay_source"], audit, file_name, row_number)
    set_if_present(row, "quota_source_year", "2026", audit, file_name, row_number)
    set_if_present(row, "permit_source", LOCK["permit_source_authority"], audit, file_name, row_number)
    set_if_present(row, "truth_source_file", LOCK["permit_overlay_source"], audit, file_name, row_number)
    set_if_present(row, "truth_source_status", LOCK["data_status"], audit, file_name, row_number)
    set_if_present(row, "missing_permits", "FALSE", audit, file_name, row_number)
    set_if_present(row, "availability_status", "total_only", audit, file_name, row_number)
    set_if_present(row, "permit_availability_type", "conservation_total_only", audit, file_name, row_number)
    set_if_present(row, "data_cutoff_date", DATA_CUTOFF_DATE, audit, file_name, row_number)

    if row.get("modeled_by_engine") == "False" or row.get("hunt_type") == LOCK["hunt_type"]:
        set_if_present(row, "probability_model", "NONE", audit, file_name, row_number)
        set_if_present(row, "display_odds_text", "Black bear conservation reference only; odds not modeled", audit, file_name, row_number)


def promote_file(path: Path, source_note: str) -> list[dict[str, str]]:
    if not path.exists():
        return []
    fieldnames, rows, encoding, newline = read_rows(path)
    audit: list[dict[str, str]] = []
    rel = path.relative_to(ROOT).as_posix()
    for index, row in enumerate(rows, start=2):
        if row.get("hunt_code") == LOCK["hunt_code"]:
            apply_updates(row, audit, rel, index, source_note)
    if audit:
        write_rows(path, fieldnames, rows, encoding, newline)
    return audit


def append_database_verification(audit_rows: list[dict[str, str]]) -> None:
    _, rows, _, _ = read_rows(DATABASE)
    for index, row in enumerate(rows, start=2):
        if row.get("hunt_code") != LOCK["hunt_code"]:
            continue
        checks = {
            "permits_2026_total": LOCK["total"],
            "permit_allotment_2026_total": LOCK["total"],
            "permit_allotment_2026_status": LOCK["permit_status"],
        }
        for field, expected in checks.items():
            current = row.get(field, "")
            audit_rows.append(
                {
                    "file": DATABASE.relative_to(ROOT).as_posix(),
                    "row_number": str(index),
                    "hunt_code": LOCK["hunt_code"],
                    "field": field,
                    "old_value": current,
                    "new_value": expected,
                    "audit_status": "VERIFIED_CANONICAL_CURRENT" if current == expected else "VERIFY_FAILED",
                }
            )


def write_lock(lock_row: dict[str, str]) -> None:
    write_rows(LOCK_CSV, LOCK_FIELDS, [lock_row])


def write_audit(rows: list[dict[str, str]]) -> None:
    write_rows(AUDIT_CSV, AUDIT_FIELDS, rows)


def write_summary(
    bear_match: dict[str, str],
    source_rows: list[dict[str, str]],
    errors: list[str],
    audit_rows: list[dict[str, str]],
) -> dict[str, object]:
    changed_rows = [row for row in audit_rows if row.get("audit_status") == "CHANGED"]
    failed = [row for row in audit_rows if row.get("audit_status") == "VERIFY_FAILED"]
    normalized_source_total_if_summed = sum(int(float(row.get("permit_count", "0") or 0)) for row in source_rows)
    pdf_source_total_if_summed = sum(int(float(row.get("permit_count", "0") or 0)) for row in PDF_EVIDENCE_ROWS)
    summary = {
        "classification": "BLACK_BEAR_CONSERVATION_BR7307_LOCK_2026",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "data_cutoff_date": DATA_CUTOFF_DATE,
        "hunt_code": LOCK["hunt_code"],
        "selected_total": int(LOCK["total"]),
        "selected_total_basis": "summed organization allocation rows for the matching conservation source row ID",
        "current_black_bear_source_present": bool(bear_match),
        "normalized_conservation_source_row_count": len(source_rows),
        "normalized_conservation_source_total_if_summed": normalized_source_total_if_summed,
        "pdf_evidence_row_count": len(PDF_EVIDENCE_ROWS),
        "pdf_evidence_total_if_summed": pdf_source_total_if_summed,
        "normalized_conservation_source_rows": [
            {
                "group": row.get("group", ""),
                "organization": row.get("organization", ""),
                "permit_count": row.get("permit_count", ""),
                "source_page_or_row": row.get("source_page_or_row", ""),
            }
            for row in source_rows
        ],
        "pdf_evidence_rows": PDF_EVIDENCE_ROWS,
        "changed_cells": len(changed_rows),
        "verified_database_current_cells": sum(
            1 for row in audit_rows if row.get("audit_status") == "VERIFIED_CANONICAL_CURRENT"
        ),
        "failed_database_verification_cells": len(failed),
        "files_changed": len({row["file"] for row in changed_rows}),
        "validation_error_count": len(errors) + len(failed),
        "validation_errors": errors + [json.dumps(row, sort_keys=True) for row in failed],
        "outputs": {
            "lock_csv": LOCK_CSV.relative_to(ROOT).as_posix(),
            "audit_csv": AUDIT_CSV.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "report_md": REPORT_MD.relative_to(ROOT).as_posix(),
        },
        "guardrail": (
            "BR7307 is locked as total-only conservation reference data. Historical 2025 draw/harvest "
            "permit fields are not changed, and no resident/nonresident split or modeled odds are invented."
        ),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def write_report(summary: dict[str, object]) -> None:
    rows = summary["pdf_evidence_rows"]
    lines = [
        "# BR7307 Black Bear Conservation Lock",
        "",
        "`BR7307` is locked as the La Sal black bear multiseason conservation reference row.",
        "",
        "## Result",
        "",
        f"- Selected current total: `{summary['selected_total']}`",
        f"- Current black bear source present: `{summary['current_black_bear_source_present']}`",
        f"- PDF evidence rows found: `{summary['pdf_evidence_row_count']}`",
        f"- PDF evidence total if summed: `{summary['pdf_evidence_total_if_summed']}`",
        f"- Normalized conservation rows found: `{summary['normalized_conservation_source_row_count']}`",
        f"- Normalized conservation total if summed: `{summary['normalized_conservation_source_total_if_summed']}`",
        f"- Failed verification cells: `{summary['failed_database_verification_cells']}`",
        "",
        "## Conservation Evidence Rows",
        "",
    ]
    for row in rows:
        lines.append(
            f"- `{row['organization']}` / `{row['group']}`: permit_count `{row['permit_count']}`, source row `{row['source_page_or_row']}`"
        )
    lines.extend(["", "## Guardrail", "", str(summary["guardrail"])])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    bear_match, source_rows, errors = validate_sources()
    lock_row = lock_output_row(source_rows)
    write_lock(lock_row)

    audit_rows: list[dict[str, str]] = []
    if not errors:
        for file_name in TARGET_FILES:
            audit_rows.extend(promote_file(ROOT / file_name, lock_row["note"]))
    append_database_verification(audit_rows)
    write_audit(audit_rows)
    summary = write_summary(bear_match, source_rows, errors, audit_rows)
    write_report(summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["validation_error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
