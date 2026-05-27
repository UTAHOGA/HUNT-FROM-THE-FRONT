"""Retire invalid 2026 current hunt-code rows from DATABASE.csv.

The retired rows are preserved in a ledger before removal so historical review
evidence remains traceable without keeping invalid codes in the current 2026
database universe.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
LEDGER = ROOT / "data_truth" / "crosswalk_truth" / "normalized" / "retired_current_hunt_codes_2026.csv"
SUMMARY = ROOT / "data_truth" / "crosswalk_truth" / "validation" / "retired_current_hunt_codes_2026_summary.json"
REPORT = ROOT / "processed_data" / "retired_current_hunt_codes_2026.md"

RETIRED_CODES = {
    "EA1007",
    "EA1053",
    "EA1287",
    "EA1288",
    "EA1289",
    "EA1290",
    "EA1291",
    "EA1292",
    "EA1293",
    "EA1294",
    "EA1295",
    "EA1296",
    "EA1297",
    "EA1298",
    "EA1299",
    "EA1300",
    "PD1039",
}
RETIREMENT_REASON = "USER_CONFIRMED_CEASES_TO_EXIST_ONLINE_EFFECTIVE_2026"


def read_database() -> tuple[list[dict[str, str]], list[str]]:
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def read_optional_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def main() -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows, columns = read_database()
    existing_ledger_rows, existing_ledger_columns = read_optional_csv(LEDGER)
    existing_retired_codes = {row.get("hunt_code", "") for row in existing_ledger_rows}
    retired_rows = [row for row in rows if row["hunt_code"] in RETIRED_CODES]
    remaining_rows = [row for row in rows if row["hunt_code"] not in RETIRED_CODES]

    found_codes = {row["hunt_code"] for row in retired_rows}
    unresolved_requested_codes = sorted(RETIRED_CODES - found_codes - existing_retired_codes)
    if unresolved_requested_codes:
        raise SystemExit(
            "Requested retired codes were not found in DATABASE.csv or the retired ledger: "
            f"{unresolved_requested_codes}"
        )

    ledger_columns = existing_ledger_columns or [
        "retired_at_utc",
        "retirement_reason",
        "effective_year",
        *columns,
    ]
    if retired_rows:
        ledger_columns = list(dict.fromkeys([*ledger_columns, "retired_at_utc", "retirement_reason", "effective_year", *columns]))
    new_ledger_rows = [
        {
            "retired_at_utc": timestamp,
            "retirement_reason": RETIREMENT_REASON,
            "effective_year": "2026",
            **row,
        }
        for row in retired_rows
    ]
    ledger_by_code = {row.get("hunt_code", ""): row for row in existing_ledger_rows}
    for row in new_ledger_rows:
        ledger_by_code[row["hunt_code"]] = row
    ledger_rows = [ledger_by_code[code] for code in sorted(RETIRED_CODES) if code in ledger_by_code]

    write_csv(DATABASE, remaining_rows, columns)
    write_csv(LEDGER, ledger_rows, ledger_columns)

    code_counts: dict[str, int] = {}
    blank_boundary_ids = 0
    for row in remaining_rows:
        code = row.get("hunt_code", "")
        code_counts[code] = code_counts.get(code, 0) + 1
        if not row.get("boundary_id", "").strip():
            blank_boundary_ids += 1

    duplicate_codes = sorted(code for code, count in code_counts.items() if count > 1)
    summary = {
        "artifact": "retired_current_hunt_codes_2026",
        "retired_at_utc": timestamp,
        "database_path": str(DATABASE.relative_to(ROOT)).replace("\\", "/"),
        "ledger_path": str(LEDGER.relative_to(ROOT)).replace("\\", "/"),
        "retirement_reason": RETIREMENT_REASON,
        "effective_year": 2026,
        "requested_retired_codes": sorted(RETIRED_CODES),
        "newly_retired_row_count": len(retired_rows),
        "newly_retired_codes": sorted(found_codes),
        "total_retired_ledger_row_count": len(ledger_rows),
        "total_retired_codes": sorted({row.get("hunt_code", "") for row in ledger_rows}),
        "database_row_count_before": len(rows),
        "database_row_count_after": len(remaining_rows),
        "database_row_delta": len(remaining_rows) - len(rows),
        "remaining_duplicate_hunt_code_count": len(duplicate_codes),
        "remaining_duplicate_hunt_codes": duplicate_codes,
        "remaining_blank_boundary_id_count": blank_boundary_ids,
        "blocker_count": len(duplicate_codes) + blank_boundary_ids,
    }

    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Retired Current Hunt Codes 2026",
        "",
        f"- Retired at UTC: `{timestamp}`",
        f"- Effective year: `2026`",
        f"- Reason: `{RETIREMENT_REASON}`",
        f"- DATABASE rows before: `{len(rows)}`",
        f"- DATABASE rows after: `{len(remaining_rows)}`",
        f"- Newly retired rows: `{len(retired_rows)}`",
        f"- Total retired ledger rows: `{len(ledger_rows)}`",
        f"- Remaining duplicate hunt codes: `{len(duplicate_codes)}`",
        f"- Remaining blank boundary IDs: `{blank_boundary_ids}`",
        "",
        "## Newly Retired Rows",
        "",
    ]
    if not retired_rows:
        lines.append("- No additional active DATABASE rows needed retirement.")
    for row in retired_rows:
        lines.append(
            "- "
            f"`{row['hunt_code']}`: {row['hunt_name']} | {row['species']} | "
            f"{row['sex_type']} | {row['weapon']} | {row['season']} | "
            f"2026 total `{row['permits_2026_total']}`"
        )
    lines.extend(["", "## Full Retired Ledger", ""])
    for row in ledger_rows:
        lines.append(
            "- "
            f"`{row['hunt_code']}`: {row['hunt_name']} | {row['species']} | "
            f"{row['sex_type']} | {row['weapon']} | {row['season']} | "
            f"2026 total `{row['permits_2026_total']}`"
        )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["blocker_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
