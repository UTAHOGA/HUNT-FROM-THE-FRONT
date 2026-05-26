"""Clear unsupported 2026 permit fields from private-land bull elk EL/LO rows.

The current DWR Hunt Planner private-land elk source publishes these hunt codes,
but does not publish 2026 permit availability or allotment numbers for them.
This script removes leaked public/EB quota values from EL/LO private-land rows
without touching public EB rows or historical 2025 fields.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE_AUDIT = ROOT / "data_truth/permit_overlay_truth/normalized/elk_private_lands_EL_LO_2026_source_audit.csv"
SOURCE_FILE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 l.e. elk.private lands  EL-2025 and LO-2026.csv"

TARGET_FILES = [
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
    ROOT / "processed_data/hunt_master_enriched.csv",
    ROOT / "processed_data/point_ladder_view.csv",
    ROOT / "processed_data/draw_reality_engine_predictive_v2.csv",
    ROOT / "data_model/runtime_drafts/point_ladder_view_v2.csv",
    ROOT / "data_model/runtime_drafts/mixed_predictive_engine_2026.materialized.csv",
    ROOT / "data_model/runtime_drafts/mixed_predictive_engine_2026.predictions.csv",
    ROOT / "data_model/harvest_quality/draw_reality_engine_predictive_with_harvest_features.csv",
    ROOT / "data_model/harvest_quality/ml_draw_predictions_with_harvest_features.csv",
    ROOT / "data/hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "data/hunt-master-canonical-2026-database-candidate.csv",
    ROOT / "processed_data/hunt_master_canonical_2026_SOURCE_OF_TRUTH_FINAL_COMPLETE_NO_PARTIALS.csv",
]

BLANK_FIELDS = {
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "permit_allotment_2026_res",
    "permit_allotment_2026_nr",
    "permit_allotment_2026_total",
    "public_permits_2026",
    "max_point_permits_2026",
    "random_permits_2026",
    "quota_2026_total",
    "quota_2026_max_pool",
    "quota_2026_random_pool",
    "display_2026_max_point_pool",
    "display_2026_random_draw",
    "guaranteed_at_2026",
    "permit_delta_2025_to_2026",
    "guaranteed_delta_2025_to_2026",
    "random_draw_odds_2026",
    "permits_year_res",
    "permits_year_nr",
    "permits_year_total",
    "prior_year_total_permits",
    "prior_year_bonus_permits",
    "prior_year_regular_permits",
    "p_quota_adjusted",
    "quota_change_weight",
}

STATUS_FIELDS = {
    "permits_2026_source": "NO_PUBLISHED_2026_PRIVATE_LAND_ELK_PERMIT_COUNT",
    "public_permits_2026_source": "NO_PUBLISHED_2026_PRIVATE_LAND_ELK_PERMIT_COUNT",
    "permit_allotment_2026_source": "NO_PUBLISHED_2026_PRIVATE_LAND_ELK_PERMIT_COUNT",
    "permit_allotment_2026_source_file": str(SOURCE_FILE.relative_to(ROOT)).replace("\\", "/"),
    "permit_allotment_2026_status": "NO_QUOTA_PUBLISHED",
    "quota_source_status": "NO_QUOTA_PUBLISHED",
    "quota_source_year": "2026",
    "quota_source_file": str(SOURCE_FILE.relative_to(ROOT)).replace("\\", "/"),
    "permit_status": "NO_QUOTA_PUBLISHED",
    "permit_allocation_type": "NO_QUOTA_PUBLISHED",
    "permit_source_authority": "Utah DWR Hunt Planner",
    "permit_note": "DWR Hunt Planner private-land elk source confirms the hunt code but publishes no 2026 permit availability or allotment number.",
}

AUDIT_OUT = ROOT / "data_truth/permit_overlay_truth/validation/elk_private_lands_EL_LO_2026_cleared_permit_fields.csv"
SUMMARY_OUT = ROOT / "data_truth/permit_overlay_truth/validation/elk_private_lands_EL_LO_2026_cleared_permit_fields_summary.json"
REPORT_OUT = ROOT / "processed_data/elk_private_lands_EL_LO_2026_cleared_permit_fields.md"

AUDIT_FIELDS = [
    "file",
    "hunt_code",
    "row_index",
    "field",
    "old_value",
    "new_value",
    "action",
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


def load_target_codes() -> set[str]:
    rows, _ = read_csv(SOURCE_AUDIT)
    codes = {row.get("hunt_code", "").strip().upper() for row in rows if row.get("hunt_code", "").strip()}
    if len(codes) != 131:
        raise RuntimeError(f"Expected 131 EL/LO target codes, found {len(codes)}")
    if {code[:2] for code in codes} != {"EL", "LO"}:
        raise RuntimeError("Target codes must only include EL and LO private-land elk rows")
    return codes


def clear_file(path: Path, target_codes: set[str]) -> tuple[list[dict[str, str]], dict[str, int]]:
    if not path.exists():
        return [], {"missing_file": 1}

    rows, fields = read_csv(path)
    audit_rows: list[dict[str, str]] = []
    counts = Counter()
    available_blank_fields = [field for field in fields if field in BLANK_FIELDS]
    available_status_fields = {field: value for field, value in STATUS_FIELDS.items() if field in fields}

    for row_index, row in enumerate(rows, start=2):
        code = row.get("hunt_code", "").strip().upper()
        if code not in target_codes:
            continue
        counts["target_rows"] += 1
        for field in available_blank_fields:
            old = row.get(field, "")
            if old:
                row[field] = ""
                counts["blanked_cells"] += 1
                audit_rows.append(
                    {
                        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                        "hunt_code": code,
                        "row_index": str(row_index),
                        "field": field,
                        "old_value": old,
                        "new_value": "",
                        "action": "BLANK_UNSUPPORTED_2026_PRIVATE_LAND_ELK_PERMIT_FIELD",
                    }
                )
        for field, new_value in available_status_fields.items():
            old = row.get(field, "")
            if old != new_value:
                row[field] = new_value
                counts["status_cells_set"] += 1
                audit_rows.append(
                    {
                        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                        "hunt_code": code,
                        "row_index": str(row_index),
                        "field": field,
                        "old_value": old,
                        "new_value": new_value,
                        "action": "SET_NO_QUOTA_PUBLISHED_STATUS",
                    }
                )

    for row in rows:
        code = row.get("hunt_code", "").strip().upper()
        if code not in target_codes:
            continue
        for field in available_blank_fields:
            if row.get(field, ""):
                counts["remaining_numeric_leak_cells"] += 1

    if audit_rows:
        write_csv(path, rows, fields)
    counts["rows"] = len(rows)
    return audit_rows, dict(counts)


def build_report(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# EL/LO Private-Lands Elk 2026 Permit-Field Cleanup",
            "",
            f"- Target EL/LO private-land elk codes: {summary['target_code_count']}",
            f"- Files inspected: {summary['files_inspected']}",
            f"- Files changed: {summary['files_changed']}",
            f"- Target rows inspected: {summary['target_rows']}",
            f"- 2026 permit/quota cells blanked: {summary['blanked_cells']}",
            f"- Status/source cells set: {summary['status_cells_set']}",
            f"- Remaining numeric leak cells: {summary['remaining_numeric_leak_cells']}",
            "",
            "Rule applied: the DWR Hunt Planner private-land elk source confirms the codes but publishes no 2026 permit availability or allotment numbers, so EL/LO rows are carried as no-quota-published reference rows. Public EB rows are not touched.",
            "",
        ]
    )


def main() -> None:
    target_codes = load_target_codes()
    all_audit_rows: list[dict[str, str]] = []
    file_summaries: dict[str, dict[str, int]] = {}
    totals = Counter()

    for path in TARGET_FILES:
        audit_rows, counts = clear_file(path, target_codes)
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        file_summaries[rel] = counts
        all_audit_rows.extend(audit_rows)
        if audit_rows:
            totals["files_changed"] += 1
        totals["files_inspected"] += 1
        totals["target_rows"] += counts.get("target_rows", 0)
        totals["blanked_cells"] += counts.get("blanked_cells", 0)
        totals["status_cells_set"] += counts.get("status_cells_set", 0)
        totals["remaining_numeric_leak_cells"] += counts.get("remaining_numeric_leak_cells", 0)

    write_csv(AUDIT_OUT, all_audit_rows, AUDIT_FIELDS)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target_code_count": len(target_codes),
        "target_prefix_counts": dict(Counter(code[:2] for code in target_codes)),
        "source_audit": str(SOURCE_AUDIT.relative_to(ROOT)).replace("\\", "/"),
        "source_file": str(SOURCE_FILE.relative_to(ROOT)).replace("\\", "/"),
        "files_inspected": totals["files_inspected"],
        "files_changed": totals["files_changed"],
        "target_rows": totals["target_rows"],
        "blanked_cells": totals["blanked_cells"],
        "status_cells_set": totals["status_cells_set"],
        "remaining_numeric_leak_cells": totals["remaining_numeric_leak_cells"],
        "file_summaries": file_summaries,
        "audit_csv": str(AUDIT_OUT.relative_to(ROOT)).replace("\\", "/"),
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    REPORT_OUT.write_text(build_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
