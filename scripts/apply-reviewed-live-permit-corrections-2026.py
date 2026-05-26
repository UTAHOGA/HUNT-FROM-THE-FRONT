"""Apply reviewed 2026 live DWR permit corrections to DATABASE.csv.

This script is intentionally narrow: it applies user-reviewed DWR Hunt Planner
permit blocks for known numeric mismatches and normalizes CWMU rows to total-only
permit shape.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
AUDIT_OUT = ROOT / "data_truth/crosswalk_truth/validation/reviewed_live_permit_corrections_2026.csv"
SUMMARY_OUT = ROOT / "data_truth/crosswalk_truth/validation/reviewed_live_permit_corrections_2026_summary.json"
REPORT_OUT = ROOT / "processed_data/reviewed_live_permit_corrections_2026.md"

REVIEWED_CORRECTIONS = {
    "BI6528": {
        "permits_2026_res": "6",
        "permits_2026_nr": "0",
        "permits_2026_total": "6",
        "reason": "Reviewed DWR Hunt Planner block: Book Cliffs, Little Creek/South archery bison resident 6 total 6.",
    },
    "BI6532": {
        "permits_2026_res": "6",
        "permits_2026_nr": "0",
        "permits_2026_total": "6",
        "reason": "Reviewed DWR Hunt Planner block: Book Cliffs, Bitter Creek archery bison resident 6 total 6.",
    },
    "BR7004": {
        "permits_2026_res": "18",
        "permits_2026_nr": "2",
        "permits_2026_total": "20",
        "reason": "Reviewed DWR Hunt Planner block: resident 18 total 20; nonresident derived as total minus resident.",
    },
    "EB3010": {
        "permits_2026_res": "10",
        "permits_2026_nr": "1",
        "permits_2026_total": "11",
        "reason": "Reviewed Monroe fire-extension DWR Hunt Planner block with extensions removed.",
    },
    "EB3047": {
        "permits_2026_res": "3",
        "permits_2026_nr": "1",
        "permits_2026_total": "4",
        "reason": "Reviewed Monroe fire-extension DWR Hunt Planner block with extensions removed.",
    },
    "EB3088": {
        "permits_2026_res": "10",
        "permits_2026_nr": "1",
        "permits_2026_total": "11",
        "reason": "Reviewed Monroe fire-extension DWR Hunt Planner block with extensions removed.",
    },
    "EB3112": {
        "permits_2026_res": "2",
        "permits_2026_nr": "0",
        "permits_2026_total": "2",
        "reason": "Reviewed Monroe fire-extension DWR Hunt Planner block with extensions removed.",
    },
    "EB3185": {
        "permits_2026_res": "18",
        "permits_2026_nr": "3",
        "permits_2026_total": "21",
        "reason": "Live DWR Hunt Planner comparison for Monroe mid any-legal-weapon fire-extension row.",
    },
}

REVIEWED_LABEL_CORRECTIONS = {
    "EB3135": {
        "weapon": "Archery",
        "reason": "Reviewed DWR Hunt Planner block: EB3135 Barney Top/Kaiparowits weapon type is Archery, not September Archery.",
    }
}


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().replace("\ufeff", "")


def numeric_text(value: str) -> str:
    text = clean(value).replace(",", "")
    if not text:
        return ""
    number = float(text)
    return str(int(number)) if number.is_integer() else str(number)


def read_database() -> tuple[list[str], list[dict[str, str]]]:
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        return fields, [{key: clean(value) for key, value in row.items()} for row in reader]


def write_database(fields: list[str], rows: list[dict[str, str]]) -> None:
    with DATABASE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def row_changed(row: dict[str, str], updates: dict[str, str]) -> bool:
    return any(row.get(field, "") != value for field, value in updates.items())


def snapshot(row: dict[str, str], prefix: str) -> dict[str, str]:
    return {
        f"{prefix}_res": row.get("permits_2026_res", ""),
        f"{prefix}_nr": row.get("permits_2026_nr", ""),
        f"{prefix}_total": row.get("permits_2026_total", ""),
        f"{prefix}_source": row.get("permits_2026_source", ""),
        f"{prefix}_status": row.get("permit_allotment_2026_status", ""),
    }


def main() -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    fields, rows = read_database()
    by_code = {row["hunt_code"]: row for row in rows}
    audit_rows: list[dict[str, str]] = []

    missing_codes = sorted(code for code in REVIEWED_CORRECTIONS if code not in by_code)
    for code, correction in REVIEWED_CORRECTIONS.items():
        if code not in by_code:
            continue
        row = by_code[code]
        before = snapshot(row, "old")
        updates = {
            "permits_2026_res": correction["permits_2026_res"],
            "permits_2026_nr": correction["permits_2026_nr"],
            "permits_2026_total": correction["permits_2026_total"],
            "permits_2026_source": "2026_DWR_HUNT_PLANNER_REVIEWED_LIVE_BLOCK",
            "permit_allotment_2026_res": correction["permits_2026_res"],
            "permit_allotment_2026_nr": correction["permits_2026_nr"],
            "permit_allotment_2026_total": correction["permits_2026_total"],
            "permit_allotment_2026_source": "2026_DWR_HUNT_PLANNER_REVIEWED_LIVE_BLOCK",
            "permit_allotment_2026_status": "REVIEWED_LIVE_DWR_SPLIT",
        }
        changed = row_changed(row, updates)
        row.update(updates)
        audit_rows.append(
            {
                "snapshot_utc": timestamp,
                "hunt_code": code,
                "hunt_name": row.get("hunt_name", ""),
                "species": row.get("species", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "action": "REVIEWED_NUMERIC_CORRECTION",
                "changed": str(changed).lower(),
                **before,
                **snapshot(row, "new"),
                "reason": correction["reason"],
            }
        )

    for code, correction in REVIEWED_LABEL_CORRECTIONS.items():
        if code not in by_code:
            continue
        row = by_code[code]
        before = snapshot(row, "old")
        old_weapon = row.get("weapon", "")
        changed = old_weapon != correction["weapon"]
        row["weapon"] = correction["weapon"]
        audit_rows.append(
            {
                "snapshot_utc": timestamp,
                "hunt_code": code,
                "hunt_name": row.get("hunt_name", ""),
                "species": row.get("species", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "action": "REVIEWED_LABEL_CORRECTION",
                "changed": str(changed).lower(),
                **before,
                **snapshot(row, "new"),
                "reason": f"{correction['reason']} Old weapon: {old_weapon}. New weapon: {correction['weapon']}.",
            }
        )

    for row in rows:
        if row.get("hunt_type") != "CWMU":
            continue
        before = snapshot(row, "old")
        total = numeric_text(row.get("permits_2026_total")) or numeric_text(row.get("permits_2026_res"))
        updates = {
            "permits_2026_res": "",
            "permits_2026_nr": "",
            "permits_2026_total": total,
            "permits_2026_source": "2026_DWR_HUNT_PLANNER_CWMU_TOTAL_ONLY",
            "permit_allotment_2026_res": "",
            "permit_allotment_2026_nr": "",
            "permit_allotment_2026_total": total,
            "permit_allotment_2026_source": "2026_DWR_HUNT_PLANNER_CWMU_TOTAL_ONLY",
            "permit_allotment_2026_status": "LIVE_DWR_CWMU_TOTAL_ONLY_FROM_QUOTA_RES",
        }
        changed = row_changed(row, updates)
        row.update(updates)
        audit_rows.append(
            {
                "snapshot_utc": timestamp,
                "hunt_code": row.get("hunt_code", ""),
                "hunt_name": row.get("hunt_name", ""),
                "species": row.get("species", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "action": "CWMU_TOTAL_ONLY_NORMALIZATION",
                "changed": str(changed).lower(),
                **before,
                **snapshot(row, "new"),
                "reason": "CWMU public permit counts are total-only in DWR hunt tables, not resident/nonresident splits.",
            }
        )

    write_database(fields, rows)
    audit_fields = [
        "snapshot_utc",
        "hunt_code",
        "hunt_name",
        "species",
        "weapon",
        "hunt_type",
        "action",
        "changed",
        "old_res",
        "old_nr",
        "old_total",
        "old_source",
        "old_status",
        "new_res",
        "new_nr",
        "new_total",
        "new_source",
        "new_status",
        "reason",
    ]
    write_csv(AUDIT_OUT, audit_rows, audit_fields)

    action_counts = Counter(row["action"] for row in audit_rows)
    changed_counts = Counter(row["action"] for row in audit_rows if row["changed"] == "true")
    cwmu_rows = [row for row in rows if row.get("hunt_type") == "CWMU"]
    cwmu_not_total_only = [
        row["hunt_code"]
        for row in cwmu_rows
        if row.get("permits_2026_res") or row.get("permits_2026_nr") or not row.get("permits_2026_total")
    ]
    summary = {
        "artifact": "reviewed_live_permit_corrections_2026",
        "snapshot_utc": timestamp,
        "missing_reviewed_codes": missing_codes,
        "reviewed_correction_codes": sorted(REVIEWED_CORRECTIONS),
        "reviewed_label_correction_codes": sorted(REVIEWED_LABEL_CORRECTIONS),
        "audit_row_count": len(audit_rows),
        "action_counts": dict(sorted(action_counts.items())),
        "changed_counts": dict(sorted(changed_counts.items())),
        "cwmu_row_count": len(cwmu_rows),
        "cwmu_not_total_only_count": len(cwmu_not_total_only),
        "cwmu_not_total_only_codes": cwmu_not_total_only[:200],
        "guardrail": "Reviewed live DWR blocks are applied narrowly; CWMU rows publish permits_2026_total only.",
        "outputs": {
            "audit_csv": AUDIT_OUT.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_OUT.relative_to(ROOT).as_posix(),
            "report_md": REPORT_OUT.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Reviewed Live Permit Corrections 2026",
        "",
        f"- Snapshot UTC: `{timestamp}`",
        f"- Reviewed correction codes: `{', '.join(sorted(REVIEWED_CORRECTIONS))}`",
        f"- CWMU rows normalized to total-only: `{len(cwmu_rows)}`",
        f"- CWMU rows not total-only after normalization: `{len(cwmu_not_total_only)}`",
        "",
        "## Action Counts",
        "",
    ]
    for action, count in sorted(action_counts.items()):
        lines.append(f"- `{action}`: `{count}`")
    lines.extend(["", "## Changed Counts", ""])
    for action, count in sorted(changed_counts.items()):
        lines.append(f"- `{action}`: `{count}`")
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if missing_codes or cwmu_not_total_only else 0


if __name__ == "__main__":
    raise SystemExit(main())
