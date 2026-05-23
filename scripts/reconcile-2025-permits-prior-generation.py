"""Compare active 2025 permit fields with prior-generation canonical data."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT / "data" / "hunt-master-canonical-2026-foundation.json"
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
NEW_HUNTS = ROOT / "processed_data" / "new_2026_rac_hunts_explain_1394_gap.csv"
OUT_JSON = ROOT / "processed_data" / "permits_2025_prior_generation_reconciliation.json"
OUT_CSV = ROOT / "processed_data" / "permits_2025_prior_generation_reconciliation.csv"
OUT_MD = ROOT / "processed_data" / "permits_2025_prior_generation_reconciliation.md"

FIELDS = ["permits_2025_res", "permits_2025_nr", "permits_2025_total"]
ACTIVE_SURFACES = [
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.csv",
    ROOT / "hunt-master-canonical-2026.json",
    ROOT / "canonical" / "hunt-planner-2026.json",
    ROOT / "generated" / "pages" / "hunt-planner.json",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.json",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.json",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    if text in {"-", "–", "—", "null", "None"}:
        return ""
    return text


def norm(value: object) -> str:
    text = clean(value).replace(",", "")
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    return str(int(number)) if number.is_integer() else str(number)


def code_of(row: dict[str, Any]) -> str:
    return clean(row.get("hunt_code") or row.get("huntCode") or row.get("code")).upper()


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def read_json_rows(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("hunt_catalog") or data.get("hunts") or data.get("records") or []
    else:
        rows = []
    fields = sorted({key for row in rows if isinstance(row, dict) for key in row.keys()})
    return fields, rows


def read_rows(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    if path.suffix.lower() == ".json":
        return read_json_rows(path)
    fields, rows = read_csv_rows(path)
    return fields, rows


def rows_by_code(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for row in rows:
        code = code_of(row)
        if code and code not in out:
            out[code] = row
    return out


def new_hunt_codes() -> list[str]:
    _, rows = read_csv_rows(NEW_HUNTS)
    return [clean(row.get("hunt_code")).upper() for row in rows if clean(row.get("hunt_code"))]


def compare_prior_to_database() -> tuple[list[dict[str, str]], dict[str, Any]]:
    _, prior_rows = read_json_rows(PRIOR)
    _, db_rows_raw = read_csv_rows(DATABASE)
    prior_rows_by_code = rows_by_code(prior_rows)
    db_rows = rows_by_code(db_rows_raw)
    prior_codes = set(prior_rows_by_code)
    db_codes = set(db_rows)
    new_codes = set(new_hunt_codes())

    rows: list[dict[str, str]] = []
    for code in sorted(prior_codes & db_codes):
        for field in FIELDS:
            prior_value = norm(prior_rows_by_code[code].get(field))
            active_value = norm(db_rows[code].get(field))
            if prior_value == active_value:
                status = "MATCH"
            elif prior_value and active_value:
                status = "DIFFERS_FROM_PRIOR_GENERATION"
            elif prior_value and not active_value:
                status = "PRIOR_ONLY"
            elif active_value and not prior_value:
                status = "ACTIVE_ONLY"
            else:
                status = "BOTH_BLANK"
            if status == "MATCH":
                continue
            rows.append(
                {
                    "hunt_code": code,
                    "hunt_name": clean(db_rows[code].get("hunt_name")),
                    "field": field,
                    "prior_generation_value": prior_value,
                    "active_value": active_value,
                    "status": status,
                    "active_source": clean(db_rows[code].get("permits_2025_source")),
                }
            )

    summary = {
        "prior_generation_file": rel(PRIOR),
        "prior_generation_hunt_code_count": len(prior_codes),
        "active_database_hunt_code_count": len(db_codes),
        "active_not_in_prior_count": len(db_codes - prior_codes),
        "active_not_in_prior_codes": sorted(db_codes - prior_codes),
        "prior_not_in_active_count": len(prior_codes - db_codes),
        "prior_not_in_active_codes": sorted(prior_codes - db_codes),
        "new_2026_gap_codes_match_active_not_prior": sorted(db_codes - prior_codes) == sorted(new_codes),
        "prior_overlap_hunt_code_count": len(prior_codes & db_codes),
        "comparison_row_count": len(rows),
        "comparison_hunt_code_count": len({row["hunt_code"] for row in rows}),
        "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
    }
    return rows, summary


def surface_checks() -> list[dict[str, Any]]:
    new_codes = set(new_hunt_codes())
    checks = []
    for path in ACTIVE_SURFACES:
        fields, rows = read_rows(path)
        by_code = rows_by_code(rows)
        missing_fields = [field for field in FIELDS if field not in fields]
        missing_keys = 0
        new_nonblank = []
        for code, row in by_code.items():
            for field in FIELDS:
                if field not in row:
                    missing_keys += 1
            if code in new_codes:
                values = [clean(row.get(field)) for field in FIELDS]
                if any(values):
                    new_nonblank.append({"hunt_code": code, "values": values})
        checks.append(
            {
                "file": rel(path),
                "row_count": len(rows),
                "hunt_code_count": len(by_code),
                "missing_required_columns_or_json_fields": missing_fields,
                "missing_json_keys_count": missing_keys if path.suffix.lower() == ".json" else 0,
                "new_2026_hunts_with_nonblank_2025_count": len(new_nonblank),
                "new_2026_hunts_with_nonblank_2025_examples": new_nonblank[:10],
            }
        )
    return checks


def write_outputs(compare_rows: list[dict[str, str]], summary: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        **summary,
        "surface_checks": checks,
        "outputs": {
            "csv": rel(OUT_CSV),
            "json": rel(OUT_JSON),
            "md": rel(OUT_MD),
        },
    }
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["hunt_code", "hunt_name", "field", "prior_generation_value", "active_value", "status", "active_source"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(compare_rows)
    lines = [
        "# 2025 Permit Prior-Generation Reconciliation",
        "",
        f"Generated UTC: {report['generated_at_utc']}",
        f"Prior generation file: `{report['prior_generation_file']}`",
        f"Prior generation hunt codes: `{report['prior_generation_hunt_code_count']}`",
        f"Active database hunt codes: `{report['active_database_hunt_code_count']}`",
        f"Active-not-prior hunt codes: `{report['active_not_in_prior_count']}`",
        f"New 2026 gap codes match active-not-prior: `{report['new_2026_gap_codes_match_active_not_prior']}`",
        f"Prior-overlap comparison rows: `{report['comparison_row_count']}` across `{report['comparison_hunt_code_count']}` hunt codes",
        "",
        "## Active Not In Prior",
        "",
        ", ".join(f"`{code}`" for code in report["active_not_in_prior_codes"]),
        "",
        "## Status Counts",
        "",
    ]
    for key, value in report["status_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Surface Checks", "", "| File | Codes | Missing fields | Missing JSON keys | New 2026 nonblank 2025 rows |", "| --- | ---: | --- | ---: | ---: |"])
    for check in checks:
        lines.append(
            f"| {check['file']} | {check['hunt_code_count']} | {', '.join(check['missing_required_columns_or_json_fields']) or 'None'} | {check['missing_json_keys_count']} | {check['new_2026_hunts_with_nonblank_2025_count']} |"
        )
    lines.extend(["", "## Note", "", "Differences from the 1394-code foundation are retained in the CSV report. Active values use `2025_DRAW_RESULTS_TABLES` when sourced from the official draw-results extraction."])
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    compare_rows, summary = compare_prior_to_database()
    checks = surface_checks()
    report = write_outputs(compare_rows, summary, checks)
    print(json.dumps({key: value for key, value in report.items() if key != "surface_checks"}, indent=2))
    failures = [
        check
        for check in checks
        if check["missing_required_columns_or_json_fields"]
        or check["missing_json_keys_count"]
        or check["new_2026_hunts_with_nonblank_2025_count"]
    ]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
