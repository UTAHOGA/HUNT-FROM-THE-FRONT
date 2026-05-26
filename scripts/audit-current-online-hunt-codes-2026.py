"""Audit canonical 2026 hunt codes against the live Utah DWR Hunt Planner.

This audit is intentionally sidecar-only: it does not edit DATABASE.csv or any
website-facing output. The goal is to isolate locally promoted/RAC rows that are
not currently present in DWR's online Hunt Planner hunt-number list.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
RETIRED_LEDGER = ROOT / "data_truth" / "crosswalk_truth" / "normalized" / "retired_current_hunt_codes_2026.csv"
RAW_OUT = (
    ROOT
    / "data_truth"
    / "crosswalk_truth"
    / "raw_inventory"
    / "live_dwr_hunt_planner_hunt_codes_snapshot_2026.csv"
)
LIVE_TABLE_OUT = (
    ROOT
    / "data_truth"
    / "crosswalk_truth"
    / "raw_inventory"
    / "live_dwr_hunt_planner_selected_tables_snapshot_2026.csv"
)
AUDIT_OUT = (
    ROOT
    / "data_truth"
    / "crosswalk_truth"
    / "validation"
    / "current_online_missing_hunt_codes_2026_review.csv"
)
SUMMARY_OUT = (
    ROOT
    / "data_truth"
    / "crosswalk_truth"
    / "validation"
    / "current_online_missing_hunt_codes_2026_review_summary.json"
)
REPORT_OUT = ROOT / "processed_data" / "current_online_missing_hunt_codes_2026_review.md"

LIVE_HUNT_CODES_URL = "https://dwrapps.utah.gov/huntboundary/HaSetup?SE=Antlerless&SP=Elk"
LIVE_TABLE_URLS = {
    ("Elk", "Antlerless"): "https://dwrapps.utah.gov/huntboundary/HuntTableData?species=Elk&gender=Antlerless",
    ("Pronghorn", "Doe"): "https://dwrapps.utah.gov/huntboundary/HuntTableData?species=Pronghorn&gender=Doe",
}

USER_REPORTED_MISSING = {"EA1007", "EA1053", "PD1039"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_optional_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return read_csv(path)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def fetch_json(url: str) -> object:
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_name(value: str) -> str:
    return " ".join((value or "").lower().replace("/", " ").replace("-", " ").split())


def live_rows_by_species_gender() -> dict[tuple[str, str], list[dict[str, object]]]:
    out: dict[tuple[str, str], list[dict[str, object]]] = {}
    for key, url in LIVE_TABLE_URLS.items():
        payload = fetch_json(url)
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected DWR HuntTableData payload for {url!r}")
        out[key] = payload
    return out


def flatten_live_tables(
    timestamp: str,
    tables: dict[tuple[str, str], list[dict[str, object]]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (species, sex_type), table_rows in tables.items():
        source_url = LIVE_TABLE_URLS[(species, sex_type)]
        for row in table_rows:
            rows.append(
                {
                    "snapshot_utc": timestamp,
                    "source_url": source_url,
                    "hunt_code": row.get("HUNT_NBR", ""),
                    "hunt_name": row.get("HUNT_NAME", ""),
                    "species": row.get("SPECIES", species),
                    "sex_type": row.get("GENDER", sex_type),
                    "weapon": row.get("WEAPON", ""),
                    "hunt_type": row.get("HUNT_TYPE", ""),
                    "season": row.get("SEASON_DATE_TEXT", ""),
                    "quota_res": row.get("QUOTA_RES", ""),
                    "quota_nres": row.get("QUOTA_NRES", ""),
                    "quota_total": row.get("QUOTA", ""),
                }
            )
    return rows


def find_live_name_candidates(
    db_row: dict[str, str],
    tables: dict[tuple[str, str], list[dict[str, object]]],
) -> str:
    key = (db_row["species"], db_row["sex_type"])
    live_rows = tables.get(key, [])
    target = normalize_name(db_row["hunt_name"])
    matches = []
    for live_row in live_rows:
        if normalize_name(str(live_row.get("HUNT_NAME", ""))) == target:
            matches.append(
                "|".join(
                    [
                        str(live_row.get("HUNT_NBR", "")),
                        str(live_row.get("HUNT_NAME", "")),
                        str(live_row.get("WEAPON", "")),
                        str(live_row.get("HUNT_TYPE", "")),
                        str(live_row.get("SEASON_DATE_TEXT", "")),
                        str(live_row.get("QUOTA", "")),
                    ]
                )
            )
    return "; ".join(matches)


def main() -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        live_payload = fetch_json(LIVE_HUNT_CODES_URL)
        live_tables = live_rows_by_species_gender()
    except (URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"Failed to fetch live DWR Hunt Planner data: {exc}", file=sys.stderr)
        return 2

    if not isinstance(live_payload, dict) or not isinstance(live_payload.get("huntNumberList"), list):
        print("Unexpected DWR HaSetup payload: missing huntNumberList", file=sys.stderr)
        return 2

    live_codes = sorted({str(code).strip() for code in live_payload["huntNumberList"] if str(code).strip()})
    live_code_set = set(live_codes)
    live_hash = sha256_text("\n".join(live_codes))

    database_rows = read_csv(DATABASE)
    retired_rows = read_optional_csv(RETIRED_LEDGER)
    retired_codes = {row.get("hunt_code", "") for row in retired_rows}
    user_reported_retired_codes = sorted(USER_REPORTED_MISSING & retired_codes)
    database_codes = {row["hunt_code"] for row in database_rows}
    missing_rows = [row for row in database_rows if row["hunt_code"] not in live_code_set]
    live_not_in_database = sorted(live_code_set - database_codes)

    raw_rows = [
        {
            "snapshot_utc": timestamp,
            "source_url": LIVE_HUNT_CODES_URL,
            "source_sha256": live_hash,
            "hunt_code": code,
        }
        for code in live_codes
    ]
    write_csv(RAW_OUT, raw_rows, ["snapshot_utc", "source_url", "source_sha256", "hunt_code"])
    live_table_rows = flatten_live_tables(timestamp, live_tables)
    write_csv(
        LIVE_TABLE_OUT,
        live_table_rows,
        [
            "snapshot_utc",
            "source_url",
            "hunt_code",
            "hunt_name",
            "species",
            "sex_type",
            "weapon",
            "hunt_type",
            "season",
            "quota_res",
            "quota_nres",
            "quota_total",
        ],
    )

    audit_rows: list[dict[str, object]] = []
    for row in missing_rows:
        code = row["hunt_code"]
        audit_rows.append(
            {
                "hunt_code": code,
                "boundary_id": row.get("boundary_id", ""),
                "hunt_name": row.get("hunt_name", ""),
                "species": row.get("species", ""),
                "sex_type": row.get("sex_type", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "season": row.get("season", ""),
                "permits_2026_res": row.get("permits_2026_res", ""),
                "permits_2026_nr": row.get("permits_2026_nr", ""),
                "permits_2026_total": row.get("permits_2026_total", ""),
                "permit_allotment_2026_status": row.get("permit_allotment_2026_status", ""),
                "permit_allotment_2026_source_file": row.get("permit_allotment_2026_source_file", ""),
                "online_status": "NOT_IN_LIVE_DWR_HUNT_PLANNER_HUNT_NUMBER_LIST",
                "issue_type": "HUNT_CODE_MISSING_ONLINE_BOUNDARY_ID_PRESENT",
                "boundary_id_status": "PRESENT_IN_DATABASE" if row.get("boundary_id", "").strip() else "BLANK_IN_DATABASE",
                "review_priority": "HIGH" if code in USER_REPORTED_MISSING else "MEDIUM",
                "user_reported_missing": "YES" if code in USER_REPORTED_MISSING else "NO",
                "live_same_name_candidates": find_live_name_candidates(row, live_tables),
                "recommended_action": (
                    "QUARANTINE_CURRENT_ONLINE_MAPPING; do not promote as live-online-current without a new DWR export"
                ),
            }
        )

    audit_fieldnames = [
        "hunt_code",
        "boundary_id",
        "hunt_name",
        "species",
        "sex_type",
        "weapon",
        "hunt_type",
        "season",
        "permits_2026_res",
        "permits_2026_nr",
        "permits_2026_total",
        "permit_allotment_2026_status",
        "permit_allotment_2026_source_file",
        "online_status",
        "issue_type",
        "boundary_id_status",
        "review_priority",
        "user_reported_missing",
        "live_same_name_candidates",
        "recommended_action",
    ]
    write_csv(AUDIT_OUT, audit_rows, audit_fieldnames)

    summary = {
        "snapshot_utc": timestamp,
        "live_hunt_codes_url": LIVE_HUNT_CODES_URL,
        "live_hunt_code_count": len(live_codes),
        "live_hunt_code_sha256": live_hash,
        "live_selected_table_row_count": len(live_table_rows),
        "live_selected_table_counts": {
            f"{species}|{sex_type}": len(rows) for (species, sex_type), rows in live_tables.items()
        },
        "database_path": str(DATABASE.relative_to(ROOT)).replace("\\", "/"),
        "database_hunt_code_count": len(database_rows),
        "database_unique_hunt_code_count": len(database_codes),
        "database_codes_missing_from_live_count": len(audit_rows),
        "live_codes_not_in_database_count": len(live_not_in_database),
        "user_reported_missing_codes": sorted(USER_REPORTED_MISSING),
        "user_reported_missing_confirmed_absent": sorted(USER_REPORTED_MISSING & {row["hunt_code"] for row in missing_rows}),
        "user_reported_missing_retired_from_database": user_reported_retired_codes,
        "retired_ledger_path": (
            str(RETIRED_LEDGER.relative_to(ROOT)).replace("\\", "/") if RETIRED_LEDGER.exists() else ""
        ),
        "missing_codes_by_prefix": {},
        "outputs": {
            "live_snapshot_csv": str(RAW_OUT.relative_to(ROOT)).replace("\\", "/"),
            "live_selected_tables_snapshot_csv": str(LIVE_TABLE_OUT.relative_to(ROOT)).replace("\\", "/"),
            "audit_csv": str(AUDIT_OUT.relative_to(ROOT)).replace("\\", "/"),
            "markdown_report": str(REPORT_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    for row in audit_rows:
        prefix = str(row["hunt_code"])[:2]
        summary["missing_codes_by_prefix"][prefix] = summary["missing_codes_by_prefix"].get(prefix, 0) + 1

    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    high_priority = [row for row in audit_rows if row["review_priority"] == "HIGH"]
    report_lines = [
        "# Current Online Missing Hunt Codes 2026",
        "",
        f"- Snapshot UTC: `{timestamp}`",
        f"- Live DWR hunt-number count: `{len(live_codes)}`",
        f"- Live selected table rows: `{len(live_table_rows)}`",
        f"- DATABASE row count: `{len(database_rows)}`",
        f"- DATABASE codes not present in live DWR Hunt Planner list: `{len(audit_rows)}`",
        f"- Missing-code rows with blank DATABASE boundary IDs: `{sum(1 for row in audit_rows if row['boundary_id_status'] == 'BLANK_IN_DATABASE')}`",
        f"- User-reported missing codes still in DATABASE and absent online: `{', '.join(summary['user_reported_missing_confirmed_absent']) or 'none'}`",
        f"- User-reported missing codes retired from DATABASE: `{', '.join(user_reported_retired_codes) or 'none'}`",
        "",
        "This is a hunt-code presence problem, not a boundary-ID gap. All rows remaining in this audit have a populated DATABASE boundary ID.",
        "",
        "## High Priority",
        "",
    ]
    if high_priority:
        for row in high_priority:
            report_lines.append(
                "- "
                f"`{row['hunt_code']}`: {row['hunt_name']} | {row['species']} | "
                f"{row['sex_type']} | {row['weapon']} | {row['season']} | "
                f"2026 total `{row['permits_2026_total']}` | source `{row['permit_allotment_2026_status']}`"
            )
    else:
        report_lines.append("- No high-priority user-reported missing codes remain in DATABASE.")
    report_lines.extend(
        [
            "",
            "## Full Missing Set",
            "",
        ]
    )
    for row in audit_rows:
        report_lines.append(
            "- "
            f"`{row['hunt_code']}`: {row['hunt_name']} | {row['species']} | "
            f"{row['sex_type']} | {row['weapon']} | {row['season']}"
        )
    report_lines.extend(
        [
            "",
            "## Recommendation",
            "",
            "Treat these rows as RAC/local evidence only until a current online DWR export confirms the hunt codes. "
            "Do not delete numeric cells from DATABASE.csv based on this audit alone, but do not promote these codes "
            "as live-online-current rows either.",
            "",
        ]
    )
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text("\n".join(report_lines), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
