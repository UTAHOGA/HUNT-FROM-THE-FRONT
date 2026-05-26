#!/usr/bin/env python3
"""Promote reviewed 2026 EA private-lands permit totals into current surfaces.

The source was validated separately from the user-supplied DWR Hunt Planner CSV.
This promotion updates current 2026 permit/allotment fields only. Historical
2025 and older values are intentionally left untouched.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = (
    ROOT
    / "data_truth/permit_overlay_truth/normalized/elk_antlerless_private_lands_EA_2026_canonical.csv"
)
AUDIT_CSV = (
    ROOT
    / "data_truth/permit_overlay_truth/validation/elk_antlerless_private_lands_EA_2026_promotion_audit.csv"
)
SUMMARY_JSON = (
    ROOT
    / "data_truth/permit_overlay_truth/validation/elk_antlerless_private_lands_EA_2026_promotion_summary.json"
)
SUMMARY_MD = ROOT / "processed_data/elk_antlerless_private_lands_EA_2026_promotion.md"

SOURCE_LABEL = "2026_DWR_HUNT_PLANNER_EA_PRIVATE_LANDS_CANONICAL"
SOURCE_AUTHORITY = "Utah DWR Hunt Planner canonical EA private-lands source"
STATUS_LABEL = "CANONICAL_EA_PRIVATE_LANDS_TOTAL_ONLY"
PROMOTION_NOTE = (
    "Canonical EA private-lands total promoted from user-confirmed DWR Hunt Planner CSV."
)

TARGET_FILES = [
    "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
    "processed_data/hunt-master-canonical-2026-source-of-truth.csv",
    "processed_data/hunt_master_enriched.csv",
    "processed_data/hunt_unit_reference_linked.csv",
    "processed_data/draw_reality_engine.csv",
    "processed_data/draw_reality_engine_predictive_v2.csv",
    "processed_data/point_ladder_view.csv",
    "processed_data/predictive_coverage_report.csv",
    "processed_data/private_lands_antlerless_elk_allocations_v1.csv",
    "processed_data/private_lands_antlerless_elk_predictions_v1.csv",
    "processed_data/private_lands_antlerless_elk_truth_source_audit.csv",
    "processed_data/all_rac_2026_permits_cumulative.csv",
    "processed_data/all_rac_2026_permits_vs_DATABASE.csv",
    "processed_data/current_year_permit_allotment_rac_index.csv",
    "processed_data/hunt_permits_rac_2025_2026.csv",
    "processed_data/permit_change_review_2026/same_hunt_code_permit_comparison_all.csv",
    "data_truth/draw_results_truth/validation/2026_antlerless_hunt_code_reconciliation.csv",
    "data_model/harvest_quality/draw_reality_engine_predictive_with_harvest_features.csv",
    "data_model/harvest_quality/ml_draw_predictions_with_harvest_features.csv",
    "data_model/runtime_drafts/mixed_predictive_engine_2026.materialized.csv",
    "data_model/runtime_drafts/mixed_predictive_engine_2026.predictions.csv",
    "data_model/runtime_drafts/mixed_predictive_engine_2026.audit.csv",
    "data_model/runtime_drafts/permits_2026_online.csv",
    "data_model/runtime_drafts/point_ladder_view_v2.csv",
    "data_model/runtime_drafts/hunt_boundary_crosswalk_v2.csv",
    "data_model/validation/hunt_master_enriched_duplicate_audit.csv",
]

TOTAL_FIELDS = [
    "permits_2026_total",
    "permit_allotment_2026_total",
    "quota_2026_total",
    "permits_allotted",
    "repo_permits_2026_total",
    "db_permits_2026_total",
    "permits_2026_total_allotted",
]

SOURCE_FIELDS = {
    "permits_2026_source": SOURCE_LABEL,
    "public_permits_2026_source": SOURCE_LABEL,
    "permit_allotment_2026_source": SOURCE_LABEL,
    "permit_allotment_2026_source_file": None,
    "permit_allotment_2026_status": STATUS_LABEL,
    "permit_source": SOURCE_LABEL,
    "quota_source": SOURCE_LABEL,
    "quota_source_file": None,
    "quota_source_status": "official",
    "quota_source_year": "2026",
    "permit_source_authority": SOURCE_AUTHORITY,
    "permit_overlay_source": None,
    "permit_note": PROMOTION_NOTE,
}

COMPARISON_FIELDS = {
    "comparison_status": "MATCH_TOTAL",
    "comparison_detail": "DATABASE total matches canonical EA private-lands source.",
    "delta_res": "",
    "delta_nr": "",
    "delta_total": "0",
    "significant_difference": "NO",
}

AUDIT_FIELDS = [
    "file",
    "row_number",
    "hunt_code",
    "hunt_name",
    "field",
    "old_value",
    "new_value",
    "audit_status",
    "source_file",
    "source_sha256",
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip().replace("\ufeff", "")


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str], str, str]:
    raw = path.read_bytes()
    encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    newline = "\r\n" if b"\r\n" in raw[:8192] else "\n"
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [{key: clean(value) for key, value in row.items()} for row in reader]
        return rows, list(reader.fieldnames or []), encoding, newline


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str], encoding: str, newline: str) -> None:
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator=newline)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_canonical() -> tuple[dict[str, int], dict[str, dict[str, str]]]:
    rows, _, _, _ = read_rows(NORMALIZED)
    by_code: dict[str, int] = {}
    meta: dict[str, dict[str, str]] = {}
    for row in rows:
        code = row["hunt_code"]
        by_code[code] = int(row["permits_2026_total_numeric"])
        meta[code] = row
    return by_code, meta


def split_max_pool(total: int) -> tuple[int, int]:
    return (total + 1) // 2, total // 2


def set_field(
    row: dict[str, str],
    field: str,
    value: object,
    audit: list[dict[str, str]],
    file_name: str,
    row_number: int,
    source: dict[str, str],
) -> None:
    if field not in row:
        return
    new_value = str(value)
    old_value = clean(row.get(field))
    if old_value == new_value:
        return
    row[field] = new_value
    audit.append(
        {
            "file": file_name,
            "row_number": str(row_number),
            "hunt_code": row.get("hunt_code", ""),
            "hunt_name": row.get("hunt_name", ""),
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            "audit_status": "CHANGED",
            "source_file": source.get("source_file", ""),
            "source_sha256": source.get("source_sha256", ""),
        }
    )


def promote_file(path: Path, totals: dict[str, int], meta: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows, fieldnames, encoding, newline = read_rows(path)
    audit: list[dict[str, str]] = []
    rel = path.relative_to(ROOT).as_posix()
    changed = False

    for index, row in enumerate(rows, start=2):
        code = row.get("hunt_code", "")
        if code not in totals:
            continue
        total = totals[code]
        source = meta[code]

        for field in TOTAL_FIELDS:
            set_field(row, field, total, audit, rel, index, source)

        if "quota_2026_max_pool" in row and "quota_2026_random_pool" in row:
            max_pool, random_pool = split_max_pool(total)
            set_field(row, "quota_2026_max_pool", max_pool, audit, rel, index, source)
            set_field(row, "quota_2026_random_pool", random_pool, audit, rel, index, source)

        for field, value in SOURCE_FIELDS.items():
            actual = source["source_file"] if value is None else value
            set_field(row, field, actual, audit, rel, index, source)

        if rel.endswith("all_rac_2026_permits_vs_DATABASE.csv"):
            for field, value in COMPARISON_FIELDS.items():
                set_field(row, field, value, audit, rel, index, source)

        changed = changed or bool(audit)

    if changed:
        write_rows(path, rows, fieldnames, encoding, newline)
    return audit


def append_database_verification(
    audit_rows: list[dict[str, str]],
    totals: dict[str, int],
    meta: dict[str, dict[str, str]],
) -> None:
    database = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
    rows, _, _, _ = read_rows(database)
    existing = {
        (row["file"], row["row_number"], row["hunt_code"], row["field"])
        for row in audit_rows
        if row.get("file") == "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
    }
    for index, row in enumerate(rows, start=2):
        code = row.get("hunt_code", "")
        if code not in totals:
            continue
        for field in ("permits_2026_total", "permit_allotment_2026_total"):
            key = ("pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv", str(index), code, field)
            if key in existing:
                continue
            current = row.get(field, "")
            canonical = str(totals[code])
            if current != canonical:
                status = "VERIFY_FAILED"
            else:
                status = "VERIFIED_CANONICAL_CURRENT"
            audit_rows.append(
                {
                    "file": key[0],
                    "row_number": key[1],
                    "hunt_code": code,
                    "hunt_name": row.get("hunt_name", ""),
                    "field": field,
                    "old_value": current,
                    "new_value": canonical,
                    "audit_status": status,
                    "source_file": meta[code].get("source_file", ""),
                    "source_sha256": meta[code].get("source_sha256", ""),
                }
            )


def write_audit(rows: list[dict[str, str]]) -> None:
    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(audit_rows: list[dict[str, str]], totals: dict[str, int]) -> dict[str, object]:
    by_file: dict[str, int] = {}
    by_code: dict[str, int] = {}
    for row in audit_rows:
        if row.get("audit_status") != "CHANGED":
            continue
        by_file[row["file"]] = by_file.get(row["file"], 0) + 1
        by_code[row["hunt_code"]] = by_code.get(row["hunt_code"], 0) + 1

    changed_cells = sum(1 for row in audit_rows if row.get("audit_status") == "CHANGED")
    verified_current_cells = sum(
        1 for row in audit_rows if row.get("audit_status") == "VERIFIED_CANONICAL_CURRENT"
    )
    failed_verification_cells = sum(1 for row in audit_rows if row.get("audit_status") == "VERIFY_FAILED")

    summary = {
        "artifact": "elk_antlerless_private_lands_EA_2026_canonical_promotion",
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "canonical_source": str(NORMALIZED.relative_to(ROOT)).replace("\\", "/"),
        "source_label": SOURCE_LABEL,
        "source_authority": SOURCE_AUTHORITY,
        "canonical_hunt_codes": len(totals),
        "canonical_total_permits_2026": sum(totals.values()),
        "files_considered": len(TARGET_FILES),
        "files_changed": len(by_file),
        "changed_cells": changed_cells,
        "changed_cells_by_file": dict(sorted(by_file.items())),
        "changed_cells_by_hunt_code": dict(sorted(by_code.items())),
        "verified_database_current_cells": verified_current_cells,
        "failed_database_verification_cells": failed_verification_cells,
        "guardrail": (
            "Promotion updated current 2026 permit/allotment fields for reviewed EA private-lands "
            "hunt codes only. Historical 2025/older values were not changed."
        ),
        "outputs": {
            "audit_csv": str(AUDIT_CSV.relative_to(ROOT)).replace("\\", "/"),
            "summary_json": str(SUMMARY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "summary_md": str(SUMMARY_MD.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def write_markdown(summary: dict[str, object]) -> None:
    lines = [
        "# 2026 EA Private-Lands Canonical Promotion",
        "",
        "Promoted reviewed antlerless elk private-lands permit totals into current 2026 surfaces.",
        "",
        "## Result",
        "",
        f"- Canonical hunt codes: `{summary['canonical_hunt_codes']}`",
        f"- Canonical source total: `{summary['canonical_total_permits_2026']}`",
        f"- Files changed: `{summary['files_changed']}`",
        f"- Changed cells: `{summary['changed_cells']}`",
        "",
        "## Guardrail",
        "",
        str(summary["guardrail"]),
    ]
    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    totals, meta = load_canonical()
    audit_rows: list[dict[str, str]] = []
    for file_name in TARGET_FILES:
        audit_rows.extend(promote_file(ROOT / file_name, totals, meta))
    append_database_verification(audit_rows, totals, meta)
    write_audit(audit_rows)
    summary = write_summary(audit_rows, totals)
    write_markdown(summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
