#!/usr/bin/env python3
"""Build a safe, DATABASE-authoritative permit overlay plan for 2026.

This script does not modify DATABASE.csv or runtime files. It turns the permit
deep-dive audit into an action queue that protects populated DATABASE numeric
2026 permit/allotment cells as Utah DWR Hunt Planner truth.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

AUDIT = ROOT / "processed_data/hunt_master_canonical_2026_built_permit_deep_dive.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"

OUTPUT = ROOT / "processed_data/database_authoritative_permit_overlay_plan_2026.csv"
SUMMARY_JSON = ROOT / "processed_data/database_authoritative_permit_overlay_plan_2026_summary.json"
SUMMARY_MD = ROOT / "processed_data/database_authoritative_permit_overlay_plan_2026.md"
VALIDATION_JSON = (
    ROOT / "data_truth/comparison_outputs/validation/database_authoritative_permit_overlay_plan_2026_summary.json"
)

TRIPLE_FIELDS = ("res", "nr", "total")

OUTPUT_FIELDS = [
    "hunt_code",
    "hunt_name",
    "species",
    "boundary_id",
    "row_origin",
    "database_numeric_protected",
    "target_database_status",
    "target_2025_total",
    "database_2025_total",
    "target_2026_total",
    "database_2026_total",
    "database_allotment_2026_total",
    "resolved_2026_res",
    "resolved_2026_nr",
    "resolved_2026_total",
    "resolved_2026_source",
    "overlay_action",
    "review_priority",
    "review_reason",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    if text in {"-", "nan", "None"}:
        return ""
    return text


def int_text(value: object) -> str:
    text = clean(value).replace(",", "")
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return ""
    return str(int(number)) if number.is_integer() else str(number)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{key: clean(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def db_triple(row: dict[str, str], prefix: str) -> tuple[str, str, str]:
    return tuple(int_text(row.get(f"{prefix}_{field}", "")) for field in TRIPLE_FIELDS)  # type: ignore[return-value]


def has_numeric(triple: tuple[str, str, str]) -> bool:
    return any(value != "" for value in triple)


def build_target_plan_row(audit_row: dict[str, str]) -> dict[str, str]:
    db_2026 = (
        int_text(audit_row.get("database_2026_res")),
        int_text(audit_row.get("database_2026_nr")),
        int_text(audit_row.get("database_2026_total")),
    )
    db_allotment = (
        int_text(audit_row.get("database_allotment_2026_res")),
        int_text(audit_row.get("database_allotment_2026_nr")),
        int_text(audit_row.get("database_allotment_2026_total")),
    )
    target_2026 = (
        int_text(audit_row.get("target_2026_res")),
        int_text(audit_row.get("target_2026_nr")),
        int_text(audit_row.get("target_2026_total")),
    )

    database_present = audit_row.get("database_present") == "YES"
    database_numeric_protected = "YES" if has_numeric(db_2026) or has_numeric(db_allotment) else "NO"

    if not database_present:
        action = "BLOCK_TARGET_CODE_NOT_IN_DATABASE"
        priority = "HIGH"
        resolved = ("", "", "")
        source = ""
        reason = "Target hunt code is absent from canonical DATABASE.csv; do not promote without source review."
    elif has_numeric(db_2026):
        status = audit_row.get("target_2026_vs_database_2026_status", "")
        if status in {"MATCH", "TOTAL_MATCH_SPLIT_DIFFERS"}:
            action = "NO_ACTION_DATABASE_MATCH"
            priority = "NONE"
            reason = "Target 2026 permits agree with populated DATABASE.csv permits."
        else:
            action = "USE_DATABASE_2026_PERMITS_IN_DERIVED_OUTPUTS"
            priority = "HIGH" if status in {"MISMATCH", "RIGHT_ONLY", "LEFT_ZERO_RIGHT_BLANK"} else "MEDIUM"
            reason = (
                "DATABASE.csv has populated 2026 permit cells. Preserve DATABASE values in derived outputs; "
                "target disagreement is review evidence only."
            )
        resolved = db_2026
        source = "DATABASE.permits_2026"
    elif has_numeric(db_allotment):
        action = "USE_DATABASE_2026_ALLOTMENT_IN_DERIVED_OUTPUTS"
        priority = "MEDIUM"
        resolved = db_allotment
        source = "DATABASE.permit_allotment_2026"
        reason = (
            "DATABASE.csv has populated 2026 allotment cells but no populated 2026 permit triple; preserve "
            "allotment values in derived outputs."
        )
    elif has_numeric(target_2026):
        action = "REVIEW_TARGET_ONLY_2026_VALUE"
        priority = "MEDIUM"
        resolved = ("", "", "")
        source = ""
        reason = "Target has 2026 values where DATABASE.csv does not; do not promote until reviewed."
    else:
        action = "NO_NUMERIC_PERMIT_DATA"
        priority = "NONE"
        resolved = ("", "", "")
        source = ""
        reason = "Neither target nor DATABASE.csv has populated 2026 permit/allotment values."

    return {
        "hunt_code": audit_row.get("hunt_code", ""),
        "hunt_name": audit_row.get("database_hunt_name") or audit_row.get("target_hunt_name", ""),
        "species": audit_row.get("database_species") or audit_row.get("target_species", ""),
        "boundary_id": audit_row.get("database_boundary_id") or audit_row.get("target_boundary_id", ""),
        "row_origin": "TARGET_AND_DATABASE" if database_present else "TARGET_ONLY",
        "database_numeric_protected": database_numeric_protected,
        "target_database_status": audit_row.get("target_2026_vs_database_2026_status", ""),
        "target_2025_total": int_text(audit_row.get("target_2025_total")),
        "database_2025_total": int_text(audit_row.get("database_2025_total")),
        "target_2026_total": target_2026[2],
        "database_2026_total": db_2026[2],
        "database_allotment_2026_total": db_allotment[2],
        "resolved_2026_res": resolved[0],
        "resolved_2026_nr": resolved[1],
        "resolved_2026_total": resolved[2],
        "resolved_2026_source": source,
        "overlay_action": action,
        "review_priority": priority,
        "review_reason": reason,
    }


def build_database_only_row(db_row: dict[str, str]) -> dict[str, str]:
    db_2026 = db_triple(db_row, "permits_2026")
    db_allotment = db_triple(db_row, "permit_allotment_2026")
    if has_numeric(db_2026):
        resolved = db_2026
        source = "DATABASE.permits_2026"
    elif has_numeric(db_allotment):
        resolved = db_allotment
        source = "DATABASE.permit_allotment_2026"
    else:
        resolved = ("", "", "")
        source = ""

    return {
        "hunt_code": clean(db_row.get("hunt_code")).upper(),
        "hunt_name": clean(db_row.get("hunt_name")),
        "species": clean(db_row.get("species")),
        "boundary_id": clean(db_row.get("boundary_id")),
        "row_origin": "DATABASE_ONLY",
        "database_numeric_protected": "YES" if has_numeric(db_2026) or has_numeric(db_allotment) else "NO",
        "target_database_status": "DATABASE_CODE_MISSING_TARGET",
        "target_2025_total": "",
        "database_2025_total": db_triple(db_row, "permits_2025")[2],
        "target_2026_total": "",
        "database_2026_total": db_2026[2],
        "database_allotment_2026_total": db_allotment[2],
        "resolved_2026_res": resolved[0],
        "resolved_2026_nr": resolved[1],
        "resolved_2026_total": resolved[2],
        "resolved_2026_source": source,
        "overlay_action": "ADD_DATABASE_CODE_TO_DERIVED_UNIVERSE",
        "review_priority": "HIGH",
        "review_reason": "Canonical DATABASE.csv contains this hunt code but target master does not.",
    }


def build_plan() -> tuple[list[dict[str, str]], dict]:
    audit_rows = read_csv(AUDIT)
    database_rows = {clean(row.get("hunt_code")).upper(): row for row in read_csv(DATABASE) if row.get("hunt_code")}

    output_rows = [build_target_plan_row(row) for row in audit_rows]
    target_codes = {row["hunt_code"] for row in output_rows if row.get("hunt_code")}

    for code in sorted(set(database_rows) - target_codes):
        output_rows.append(build_database_only_row(database_rows[code]))

    action_counts = Counter(row["overlay_action"] for row in output_rows)
    priority_counts = Counter(row["review_priority"] for row in output_rows)
    origin_counts = Counter(row["row_origin"] for row in output_rows)
    protected_rows = sum(1 for row in output_rows if row["database_numeric_protected"] == "YES")

    blockers = [
        row["hunt_code"]
        for row in output_rows
        if row["overlay_action"] in {"BLOCK_TARGET_CODE_NOT_IN_DATABASE"}
    ]

    summary = {
        "artifact": "database_authoritative_permit_overlay_plan_2026",
        "source_audit": AUDIT.relative_to(ROOT).as_posix(),
        "database_file": str(DATABASE).replace("\\", "/"),
        "output_row_count": len(output_rows),
        "unique_hunt_codes": len({row["hunt_code"] for row in output_rows if row["hunt_code"]}),
        "database_numeric_protected_rows": protected_rows,
        "target_only_blocker_codes": blockers,
        "action_counts": dict(sorted(action_counts.items())),
        "review_priority_counts": dict(sorted(priority_counts.items())),
        "row_origin_counts": dict(sorted(origin_counts.items())),
        "guardrail": (
            "Populated numeric 2026 permit/allotment cells in canonical DATABASE.csv are direct Utah DWR Hunt "
            "Planner truth. Populated 2025 or older permit fields with reviewed source lineage are canonical "
            "historical source truth and must not drift. "
            "This plan only directs derived outputs to use DATABASE values where populated; it does not modify "
            "DATABASE.csv or promote comparison-source values over DATABASE.csv."
        ),
        "outputs": {
            "csv": OUTPUT.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "summary_md": SUMMARY_MD.relative_to(ROOT).as_posix(),
            "validation_json": VALIDATION_JSON.relative_to(ROOT).as_posix(),
        },
    }
    return output_rows, summary


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in OUTPUT_FIELDS})


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(summary: dict) -> None:
    lines = [
        "# Database Authoritative Permit Overlay Plan 2026",
        "",
        "This is a reviewable action queue. It does not modify `DATABASE.csv` or runtime files.",
        "",
        "## Summary",
        "",
        f"- Output rows: `{summary['output_row_count']}`",
        f"- Unique hunt codes: `{summary['unique_hunt_codes']}`",
        f"- Database numeric protected rows: `{summary['database_numeric_protected_rows']}`",
        f"- Target-only blocker codes: `{len(summary['target_only_blocker_codes'])}`",
        "",
        "## Guardrail",
        "",
        summary["guardrail"],
        "",
        "## Action Counts",
        "",
    ]
    for action, count in summary["action_counts"].items():
        lines.append(f"- `{action}`: `{count}`")
    lines.extend(["", "## Review Priority Counts", ""])
    for priority, count in summary["review_priority_counts"].items():
        lines.append(f"- `{priority}`: `{count}`")
    lines.extend(["", "## Row Origin Counts", ""])
    for origin, count in summary["row_origin_counts"].items():
        lines.append(f"- `{origin}`: `{count}`")
    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows, summary = build_plan()
    write_csv(OUTPUT, rows)
    write_json(SUMMARY_JSON, summary)
    write_json(VALIDATION_JSON, summary)
    write_markdown(summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
