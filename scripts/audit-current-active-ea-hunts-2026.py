"""Reconcile current DATABASE EA rows against live/current antlerless elk EA hunts.

This audit does not modify DATABASE.csv. It records whether each live DWR
Hunt Planner antlerless elk hunt code is present in DATABASE and whether
DATABASE carries any extra active EA rows outside the live/current EA set.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
RETIRED_LEDGER = ROOT / "data_truth" / "crosswalk_truth" / "normalized" / "retired_current_hunt_codes_2026.csv"
LIVE_EA_URL = "https://dwrapps.utah.gov/huntboundary/HuntTableData?species=Elk&gender=Antlerless"

AUDIT = ROOT / "data_truth" / "crosswalk_truth" / "validation" / "current_active_ea_hunts_2026_reconciliation.csv"
SUMMARY = ROOT / "data_truth" / "crosswalk_truth" / "validation" / "current_active_ea_hunts_2026_reconciliation_summary.json"
REPORT = ROOT / "processed_data" / "current_active_ea_hunts_2026_reconciliation.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_optional_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return read_csv(path)


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def fetch_live_ea_rows() -> list[dict[str, object]]:
    with urlopen(LIVE_EA_URL, timeout=30) as response:
        rows = json.load(response)
    if not isinstance(rows, list):
        raise RuntimeError("Unexpected DWR Hunt Planner EA payload")
    return [row for row in rows if str(row.get("HUNT_NBR", "")).startswith("EA")]


def main() -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    live_rows = fetch_live_ea_rows()
    db_rows = [row for row in read_csv(DATABASE) if row.get("hunt_code", "").startswith("EA")]
    retired_rows = [row for row in read_optional_csv(RETIRED_LEDGER) if row.get("hunt_code", "").startswith("EA")]

    live_by_code = {str(row["HUNT_NBR"]): row for row in live_rows}
    db_by_code = {row["hunt_code"]: row for row in db_rows}
    retired_by_code = {row["hunt_code"]: row for row in retired_rows}

    audit_rows: list[dict[str, object]] = []
    for code in sorted(set(live_by_code) | set(db_by_code)):
        live = live_by_code.get(code, {})
        db = db_by_code.get(code, {})
        retired = retired_by_code.get(code, {})
        if code in live_by_code and code in db_by_code:
            status = "ACTIVE_EA_CONFIRMED_IN_DATABASE"
            action = "KEEP_ACTIVE"
        elif code in live_by_code and code not in db_by_code:
            status = "ACTIVE_EA_MISSING_FROM_DATABASE"
            action = "ADD_OR_REPAIR_DATABASE"
        else:
            status = "DATABASE_EA_EXTRA_NOT_IN_CURRENT_ACTIVE_LIST"
            action = "REVIEW_FOR_RETIREMENT_OR_CODE_REMAP"
        audit_rows.append(
            {
                "hunt_code": code,
                "status": status,
                "recommended_action": action,
                "database_hunt_name": db.get("hunt_name", ""),
                "live_hunt_name": live.get("HUNT_NAME", ""),
                "database_season": db.get("season", ""),
                "live_season": live.get("SEASON_DATE_TEXT", ""),
                "database_res": db.get("permits_2026_res", ""),
                "database_nonres": db.get("permits_2026_nr", ""),
                "database_total": db.get("permits_2026_total", ""),
                "live_res": live.get("QUOTA_RES", ""),
                "live_nonres": live.get("QUOTA_NRES", ""),
                "live_total": live.get("QUOTA", ""),
                "retired_ledger_status": "RETIRED" if retired else "",
                "retirement_reason": retired.get("retirement_reason", ""),
            }
        )

    status_counts: dict[str, int] = {}
    for row in audit_rows:
        status_counts[str(row["status"])] = status_counts.get(str(row["status"]), 0) + 1

    extra_codes = [
        str(row["hunt_code"])
        for row in audit_rows
        if row["status"] == "DATABASE_EA_EXTRA_NOT_IN_CURRENT_ACTIVE_LIST"
    ]
    missing_codes = [
        str(row["hunt_code"])
        for row in audit_rows
        if row["status"] == "ACTIVE_EA_MISSING_FROM_DATABASE"
    ]

    columns = [
        "hunt_code",
        "status",
        "recommended_action",
        "database_hunt_name",
        "live_hunt_name",
        "database_season",
        "live_season",
        "database_res",
        "database_nonres",
        "database_total",
        "live_res",
        "live_nonres",
        "live_total",
        "retired_ledger_status",
        "retirement_reason",
    ]
    write_csv(AUDIT, audit_rows, columns)

    summary = {
        "artifact": "current_active_ea_hunts_2026_reconciliation",
        "snapshot_utc": timestamp,
        "live_source_url": LIVE_EA_URL,
        "database_path": str(DATABASE.relative_to(ROOT)).replace("\\", "/"),
        "live_active_ea_count": len(live_by_code),
        "database_ea_count": len(db_by_code),
        "retired_ea_count": len(retired_by_code),
        "status_counts": dict(sorted(status_counts.items())),
        "active_ea_missing_from_database_count": len(missing_codes),
        "active_ea_missing_from_database_codes": missing_codes,
        "database_extra_not_current_active_count": len(extra_codes),
        "database_extra_not_current_active_codes": extra_codes,
        "blocker_count": len(missing_codes),
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Current Active EA Hunts 2026 Reconciliation",
        "",
        f"- Snapshot UTC: `{timestamp}`",
        f"- Live/current active EA count: `{len(live_by_code)}`",
        f"- DATABASE EA count: `{len(db_by_code)}`",
        f"- Active EA missing from DATABASE: `{len(missing_codes)}`",
        f"- DATABASE extra EA not in current active list: `{len(extra_codes)}`",
        "",
        "## Result",
        "",
        "All live/current active `EA` hunt codes are present in DATABASE. The only mismatch is extra DATABASE `EA` rows that do not appear in the current active list.",
        "",
        "## DATABASE Extra EA Rows",
        "",
    ]
    for code in extra_codes:
        row = db_by_code[code]
        lines.append(
            "- "
            f"`{code}`: {row['hunt_name']} | {row['weapon']} | {row['season']} | total `{row['permits_2026_total']}`"
        )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["blocker_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
