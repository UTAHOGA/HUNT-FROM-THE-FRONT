"""Pull live Utah DWR Hunt Planner permit numbers for reviewed table endpoints.

This is a sidecar audit only. It snapshots DWR's live HuntTableData quota
columns and compares them to canonical DATABASE.csv without changing DATABASE.
"""

from __future__ import annotations

import csv
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"

LIVE_TABLE_URLS = {
    ("Elk", "Antlerless"): "https://dwrapps.utah.gov/huntboundary/HuntTableData?species=Elk&gender=Antlerless",
    ("Pronghorn", "Doe"): "https://dwrapps.utah.gov/huntboundary/HuntTableData?species=Pronghorn&gender=Doe",
}
TOTAL_ONLY_TYPES = {"CWMU", "Private Lands Only", "Conservation", "Expo", "Antlerless Elk Control"}

RAW_OUT = (
    ROOT
    / "data_truth"
    / "crosswalk_truth"
    / "raw_inventory"
    / "live_dwr_hunt_planner_permit_numbers_2026.csv"
)
COMPARE_OUT = (
    ROOT
    / "data_truth"
    / "crosswalk_truth"
    / "validation"
    / "live_dwr_permit_numbers_vs_DATABASE_2026.csv"
)
SUMMARY_OUT = (
    ROOT
    / "data_truth"
    / "crosswalk_truth"
    / "validation"
    / "live_dwr_permit_numbers_vs_DATABASE_2026_summary.json"
)
REPORT_OUT = ROOT / "processed_data/live_dwr_permit_numbers_vs_DATABASE_2026.md"
REQUEST_HEADERS = {
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://dwrapps.utah.gov/huntboundary/hbstart",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
}


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    return "" if text in {"", "-", "nan", "None"} else text


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


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def fetch_json(source_url: str) -> object:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        request = Request(source_url, headers=REQUEST_HEADERS)
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Unable to fetch DWR HuntTableData after retries: {source_url}") from last_error


def fetch_live_rows(timestamp: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (species, sex_type), source_url in LIVE_TABLE_URLS.items():
        payload = fetch_json(source_url)
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected DWR payload for {source_url}")
        for row in payload:
            rows.append(
                {
                    "snapshot_utc": timestamp,
                    "source_url": source_url,
                    "hunt_code": clean(row.get("HUNT_NBR")).upper(),
                    "hunt_name": clean(row.get("HUNT_NAME")),
                    "species": clean(row.get("SPECIES")) or species,
                    "sex_type": clean(row.get("GENDER")) or sex_type,
                    "weapon": clean(row.get("WEAPON")),
                    "hunt_type": clean(row.get("HUNT_TYPE")),
                    "season": clean(row.get("SEASON_DATE_TEXT")),
                    "live_res": int_text(row.get("QUOTA_RES")),
                    "live_nr": int_text(row.get("QUOTA_NRES")),
                    "live_total": int_text(row.get("QUOTA")),
                }
            )
    return rows


def db_selected_rows() -> list[dict[str, str]]:
    allowed = set(LIVE_TABLE_URLS)
    rows = []
    for row in read_csv(DATABASE):
        key = (clean(row.get("species")), clean(row.get("sex_type")))
        if key in allowed:
            rows.append(row)
    return rows


def compare_triple(live: tuple[str, str, str], database: tuple[str, str, str]) -> str:
    if not any(live) and not any(database):
        return "BOTH_BLANK"
    if any(live) and not any(database):
        return "LIVE_HAS_NUMERIC_DATABASE_BLANK"
    if any(database) and not any(live):
        return "DATABASE_HAS_NUMERIC_LIVE_BLANK"
    if live == database:
        return "MATCH"
    if live[2] and database[2] and live[2] == database[2]:
        return "TOTAL_MATCH_SPLIT_DIFFERS"
    return "NUMERIC_MISMATCH"


def live_shape(row: dict[str, object]) -> tuple[str, str, str, str]:
    hunt_type = clean(row.get("hunt_type"))
    live_res = int_text(row.get("live_res"))
    live_nr = int_text(row.get("live_nr"))
    live_total = int_text(row.get("live_total"))
    if hunt_type == "CWMU":
        return "", "", live_res or live_total, "LIVE_DWR_CWMU_TOTAL_ONLY_FROM_QUOTA_RES"
    if hunt_type in TOTAL_ONLY_TYPES:
        total = live_total or live_res
        if total in {"", "0"}:
            return "", "", "", "LIVE_DWR_NO_QUOTA_PUBLISHED"
        return "", "", total, "LIVE_DWR_TOTAL_ONLY"
    if live_total in {"", "0"} and live_res in {"", "0"} and live_nr in {"", "0"}:
        return "", "", "", "LIVE_DWR_NO_QUOTA_PUBLISHED"
    return live_res, live_nr, live_total, "LIVE_DWR_RES_NR_SPLIT"


def build_compare(live_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    live_by_code = {str(row["hunt_code"]): row for row in live_rows if row.get("hunt_code")}
    db_by_code = {row["hunt_code"]: row for row in db_selected_rows() if row.get("hunt_code")}
    rows: list[dict[str, object]] = []
    for code in sorted(set(live_by_code) | set(db_by_code)):
        live = live_by_code.get(code, {})
        db = db_by_code.get(code, {})
        live_raw_triple = (
            int_text(live.get("live_res")),
            int_text(live.get("live_nr")),
            int_text(live.get("live_total")),
        )
        live_triple = ("", "", "", "")
        live_shape_status = ""
        if live:
            live_res, live_nr, live_total, live_shape_status = live_shape(live)
            live_triple = (live_res, live_nr, live_total)
        db_triple = (
            int_text(db.get("permits_2026_res")),
            int_text(db.get("permits_2026_nr")),
            int_text(db.get("permits_2026_total")),
        )
        allotment_triple = (
            int_text(db.get("permit_allotment_2026_res")),
            int_text(db.get("permit_allotment_2026_nr")),
            int_text(db.get("permit_allotment_2026_total")),
        )
        if any(db_triple):
            compare_triple_source = "DATABASE.permits_2026"
            compare_db_triple = db_triple
        elif any(allotment_triple):
            compare_triple_source = "DATABASE.permit_allotment_2026"
            compare_db_triple = allotment_triple
        else:
            compare_triple_source = ""
            compare_db_triple = ("", "", "")
        if live and db:
            presence_status = "LIVE_AND_DATABASE"
        elif live:
            presence_status = "LIVE_ONLY"
        else:
            presence_status = "DATABASE_ONLY"
        if live and db and live_shape_status == "LIVE_DWR_NO_QUOTA_PUBLISHED":
            comparison_status = (
                "LIVE_NO_QUOTA_DATABASE_PRESERVED" if any(compare_db_triple) else "BOTH_BLANK"
            )
        else:
            comparison_status = compare_triple(live_triple, compare_db_triple) if live and db else presence_status
        rows.append(
            {
                "hunt_code": code,
                "presence_status": presence_status,
                "comparison_status": comparison_status,
                "live_shape_status": live_shape_status,
                "database_compare_source": compare_triple_source,
                "source_url": live.get("source_url", ""),
                "live_hunt_name": live.get("hunt_name", ""),
                "database_hunt_name": db.get("hunt_name", ""),
                "live_species": live.get("species", ""),
                "database_species": db.get("species", ""),
                "live_sex_type": live.get("sex_type", ""),
                "database_sex_type": db.get("sex_type", ""),
                "live_weapon": live.get("weapon", ""),
                "database_weapon": db.get("weapon", ""),
                "live_hunt_type": live.get("hunt_type", ""),
                "database_hunt_type": db.get("hunt_type", ""),
                "live_season": live.get("season", ""),
                "database_season": db.get("season", ""),
                "live_raw_res": live_raw_triple[0],
                "live_raw_nr": live_raw_triple[1],
                "live_raw_total": live_raw_triple[2],
                "live_res": live_triple[0],
                "live_nr": live_triple[1],
                "live_total": live_triple[2],
                "database_res": db_triple[0],
                "database_nr": db_triple[1],
                "database_total": db_triple[2],
                "database_allotment_res": allotment_triple[0],
                "database_allotment_nr": allotment_triple[1],
                "database_allotment_total": allotment_triple[2],
                "database_compared_res": compare_db_triple[0],
                "database_compared_nr": compare_db_triple[1],
                "database_compared_total": compare_db_triple[2],
            }
        )
    return rows


def main() -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    live_rows = fetch_live_rows(timestamp)
    compare_rows = build_compare(live_rows)

    raw_fields = [
        "snapshot_utc",
        "source_url",
        "hunt_code",
        "hunt_name",
        "species",
        "sex_type",
        "weapon",
        "hunt_type",
        "season",
        "live_res",
        "live_nr",
        "live_total",
    ]
    compare_fields = [
        "hunt_code",
        "presence_status",
        "comparison_status",
        "live_shape_status",
        "database_compare_source",
        "source_url",
        "live_hunt_name",
        "database_hunt_name",
        "live_species",
        "database_species",
        "live_sex_type",
        "database_sex_type",
        "live_weapon",
        "database_weapon",
        "live_hunt_type",
        "database_hunt_type",
        "live_season",
        "database_season",
        "live_raw_res",
        "live_raw_nr",
        "live_raw_total",
        "live_res",
        "live_nr",
        "live_total",
        "database_res",
        "database_nr",
        "database_total",
        "database_allotment_res",
        "database_allotment_nr",
        "database_allotment_total",
        "database_compared_res",
        "database_compared_nr",
        "database_compared_total",
    ]
    write_csv(RAW_OUT, live_rows, raw_fields)
    write_csv(COMPARE_OUT, compare_rows, compare_fields)

    comparison_counts = Counter(str(row["comparison_status"]) for row in compare_rows)
    presence_counts = Counter(str(row["presence_status"]) for row in compare_rows)
    numeric_mismatches = [
        row
        for row in compare_rows
        if row["comparison_status"] in {"NUMERIC_MISMATCH", "TOTAL_MATCH_SPLIT_DIFFERS"}
    ]
    live_only = [row for row in compare_rows if row["presence_status"] == "LIVE_ONLY"]
    database_only = [row for row in compare_rows if row["presence_status"] == "DATABASE_ONLY"]
    summary = {
        "artifact": "live_dwr_permit_numbers_vs_DATABASE_2026",
        "snapshot_utc": timestamp,
        "source_urls": {f"{species}|{sex_type}": url for (species, sex_type), url in LIVE_TABLE_URLS.items()},
        "live_row_count": len(live_rows),
        "comparison_row_count": len(compare_rows),
        "presence_counts": dict(sorted(presence_counts.items())),
        "comparison_status_counts": dict(sorted(comparison_counts.items())),
        "numeric_mismatch_count": len(numeric_mismatches),
        "live_only_count": len(live_only),
        "database_only_count": len(database_only),
        "numeric_mismatch_codes": [str(row["hunt_code"]) for row in numeric_mismatches],
        "live_only_codes": [str(row["hunt_code"]) for row in live_only],
        "database_only_codes": [str(row["hunt_code"]) for row in database_only],
        "guardrail": "This pull snapshots live DWR permit numbers for reviewed HuntTableData endpoints only. It does not modify DATABASE.csv.",
        "outputs": {
            "raw_csv": RAW_OUT.relative_to(ROOT).as_posix(),
            "comparison_csv": COMPARE_OUT.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_OUT.relative_to(ROOT).as_posix(),
            "report_md": REPORT_OUT.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Live DWR Permit Numbers vs DATABASE 2026",
        "",
        f"- Snapshot UTC: `{timestamp}`",
        f"- Live permit rows: `{len(live_rows)}`",
        f"- Comparison rows: `{len(compare_rows)}`",
        f"- Numeric mismatch rows: `{len(numeric_mismatches)}`",
        f"- Live-only rows: `{len(live_only)}`",
        f"- DATABASE-only rows: `{len(database_only)}`",
        "",
        "## Source URLs",
        "",
    ]
    for label, url in summary["source_urls"].items():
        lines.append(f"- `{label}`: {url}")
    lines.extend(["", "## Status Counts", ""])
    for status, count in summary["comparison_status_counts"].items():
        lines.append(f"- `{status}`: `{count}`")
    if numeric_mismatches:
        lines.extend(["", "## Numeric Mismatches", ""])
        for row in numeric_mismatches:
            lines.append(
                f"- `{row['hunt_code']}`: live `{row['live_res']}/{row['live_nr']}/{row['live_total']}` "
                f"vs {row['database_compare_source']} "
                f"`{row['database_compared_res']}/{row['database_compared_nr']}/{row['database_compared_total']}`"
            )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
