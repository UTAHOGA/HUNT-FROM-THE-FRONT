"""Promote 2025 draw-results permit totals into explicit permits_2025_* fields.

Source data comes from the local official draw-results extraction:
`draw_results_long_cumulative_2025_draw_folder_DATABASE_ALIGNED_V3.csv`.

The promoted `permits_2025_*` values are aggregate draw-table permit totals by
hunt_code and residency. They are intentionally separate from 2026 RAC current
allotments (`permit_allotment_2026_*`) and from point-level draw-result detail.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "draw_results_long_cumulative_2025_draw_folder_DATABASE_ALIGNED_V3.csv"
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
OUT_DIR = ROOT / "processed_data"
REPORT_JSON = OUT_DIR / "permits_2025_draw_results_promotion_report.json"
REPORT_CSV = OUT_DIR / "permits_2025_draw_results_promotion_report.csv"
REPORT_MD = OUT_DIR / "permits_2025_draw_results_promotion_report.md"

PROMOTED_FIELDS = [
    "permits_2025_res",
    "permits_2025_nr",
    "permits_2025_total",
    "permits_2025_source",
]
SOURCE_LABEL = "2025_DRAW_RESULTS_TABLES"

CSV_TARGETS = [
    DATABASE,
    ROOT / "processed_data" / "hunt_master_enriched.csv",
    ROOT / "processed_data" / "hunt_unit_reference_linked.csv",
    ROOT / "processed_data" / "point_ladder_view.csv",
    ROOT / "processed_data" / "draw_reality_engine.csv",
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.csv",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.csv",
]

JSON_TARGETS = [
    ROOT / "hunt-master-canonical-2026.json",
    ROOT / "canonical" / "hunt-planner-2026.json",
    ROOT / "generated" / "pages" / "hunt-planner.json",
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.json",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.json",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.json",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    if text in {"", "-", "–", "—", "null", "None"}:
        return ""
    return text


def as_number(value: object) -> float:
    text = clean(value).replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def format_int(value: float) -> str:
    if value == 0:
        return "0"
    return str(int(value)) if float(value).is_integer() else str(value)


def code_of(row: dict[str, Any]) -> str:
    return clean(row.get("hunt_code") or row.get("huntCode") or row.get("code")).upper()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def insert_fields(fieldnames: list[str]) -> list[str]:
    out = list(fieldnames)
    anchor = None
    for candidate in ("permits_2025_draw_source", "permits_2025_draw_total", "permits_2026_total", "hunt_type"):
        if candidate in out:
            anchor = candidate
            break
    index = out.index(anchor) + 1 if anchor else len(out)
    for field in PROMOTED_FIELDS:
        if field not in out:
            out.insert(index, field)
            index += 1
    return out


def database_codes() -> set[str]:
    _, rows = read_csv(DATABASE)
    return {code_of(row) for row in rows if code_of(row)}


def build_source() -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    db_codes = database_codes()
    totals: dict[str, dict[str, float]] = defaultdict(lambda: {"Resident": 0.0, "Nonresident": 0.0})
    source_files: dict[str, set[str]] = defaultdict(set)
    source_pages: dict[str, set[str]] = defaultdict(set)
    row_count = 0
    used_row_count = 0
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            row_count += 1
            code = code_of(row)
            if clean(row.get("year")) != "2025" or code not in db_codes:
                continue
            residency = clean(row.get("residency"))
            if residency not in {"Resident", "Nonresident"}:
                continue
            total_permits = as_number(row.get("total_permits"))
            totals[code][residency] += total_permits
            if clean(row.get("source_file")):
                source_files[code].add(clean(row.get("source_file")))
            if clean(row.get("page_number")):
                source_pages[code].add(clean(row.get("page_number")))
            used_row_count += 1

    source: dict[str, dict[str, str]] = {}
    for code, values in totals.items():
        res = values["Resident"]
        nr = values["Nonresident"]
        source[code] = {
            "permits_2025_res": format_int(res),
            "permits_2025_nr": format_int(nr),
            "permits_2025_total": format_int(res + nr),
            "permits_2025_source": SOURCE_LABEL,
            "permits_2025_source_files": "|".join(sorted(source_files.get(code, set()))),
            "permits_2025_source_pages": "|".join(sorted(source_pages.get(code, set()))),
        }

    metadata = {
        "source_rows": row_count,
        "source_rows_used": used_row_count,
        "database_hunt_codes": len(db_codes),
        "source_hunt_codes": len(source),
        "source_hunt_codes_with_nonzero_total": sum(1 for row in source.values() if as_number(row["permits_2025_total"]) > 0),
    }
    return source, metadata


def patch_row(row: dict[str, Any], source_values: dict[str, str]) -> int:
    changed = 0
    for field in PROMOTED_FIELDS:
        value = source_values.get(field, "")
        if clean(row.get(field)) != value:
            row[field] = value
            changed += 1
    return changed


def patch_csv(path: Path, source: dict[str, dict[str, str]]) -> dict[str, Any]:
    if not path.exists():
        return {"file": rel(path), "kind": "csv", "status": "missing", "rows_checked": 0, "matched_hunt_codes": 0, "rows_changed": 0, "changed_cells": 0}
    fieldnames, rows = read_csv(path)
    fieldnames = insert_fields(fieldnames)
    matched: set[str] = set()
    changed_cells = 0
    rows_changed = 0
    for row in rows:
        for field in fieldnames:
            row.setdefault(field, "")
        code = code_of(row)
        if code not in source:
            continue
        matched.add(code)
        row_changes = patch_row(row, source[code])
        if row_changes:
            rows_changed += 1
            changed_cells += row_changes
    write_csv(path, fieldnames, rows)
    return {
        "file": rel(path),
        "kind": "csv",
        "status": "written",
        "rows_checked": len(rows),
        "matched_hunt_codes": len(matched),
        "rows_changed": rows_changed,
        "changed_cells": changed_cells,
    }


def json_rows(data: Any) -> tuple[list[dict[str, Any]], str]:
    if isinstance(data, list):
        return data, "root_array"
    if isinstance(data, dict):
        for key in ("hunt_catalog", "hunts", "records"):
            rows = data.get(key)
            if isinstance(rows, list):
                return rows, key
    return [], "unsupported"


def patch_json(path: Path, source: dict[str, dict[str, str]]) -> dict[str, Any]:
    if not path.exists():
        return {"file": rel(path), "kind": "json", "status": "missing", "rows_checked": 0, "matched_hunt_codes": 0, "rows_changed": 0, "changed_cells": 0}
    data = json.loads(path.read_text(encoding="utf-8"))
    rows, container = json_rows(data)
    matched: set[str] = set()
    changed_cells = 0
    rows_changed = 0
    for row in rows:
        for field in PROMOTED_FIELDS:
            if field not in row:
                row[field] = ""
                changed_cells += 1
                rows_changed += 1
        code = code_of(row)
        if code not in source:
            continue
        matched.add(code)
        row_changes = patch_row(row, source[code])
        if row_changes:
            rows_changed += 1
            changed_cells += row_changes
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "file": rel(path),
        "kind": "json",
        "container": container,
        "status": "written",
        "rows_checked": len(rows),
        "matched_hunt_codes": len(matched),
        "rows_changed": rows_changed,
        "changed_cells": changed_cells,
    }


def spot_checks(source: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    checks = []
    for code in ["DB1002", "EB3024", "EA1010", "PB5025", "BR1008", "PD1039"]:
        values = source.get(code, {})
        checks.append(
            {
                "hunt_code": code,
                "permits_2025_res": values.get("permits_2025_res", ""),
                "permits_2025_nr": values.get("permits_2025_nr", ""),
                "permits_2025_total": values.get("permits_2025_total", ""),
                "source_files": values.get("permits_2025_source_files", ""),
            }
        )
    return checks


def validate_against_draw_fields(source: dict[str, dict[str, str]]) -> dict[str, Any]:
    _, rows = read_csv(DATABASE)
    mismatches = []
    for row in rows:
        code = code_of(row)
        if code not in source or not clean(row.get("permits_2025_draw_total")):
            continue
        if clean(row.get("permits_2025_draw_total")) != source[code]["permits_2025_total"]:
            mismatches.append(
                {
                    "hunt_code": code,
                    "hunt_name": clean(row.get("hunt_name")),
                    "permits_2025_total": source[code]["permits_2025_total"],
                    "permits_2025_draw_total": clean(row.get("permits_2025_draw_total")),
                }
            )
    return {
        "draw_field_total_mismatch_count": len(mismatches),
        "draw_field_total_mismatch_examples": mismatches[:25],
    }


def write_reports(results: list[dict[str, Any]], source: dict[str, dict[str, str]], metadata: dict[str, Any]) -> dict[str, Any]:
    status_counts = Counter(result["status"] for result in results)
    validation = validate_against_draw_fields(source)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": rel(SOURCE),
        **metadata,
        **validation,
        "files_written": sum(1 for result in results if result["status"] == "written"),
        "total_rows_changed": sum(int(result.get("rows_changed", 0)) for result in results),
        "total_changed_cells": sum(int(result.get("changed_cells", 0)) for result in results),
        "status_counts": dict(sorted(status_counts.items())),
        "spot_checks": spot_checks(source),
        "results": results,
    }
    REPORT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with REPORT_CSV.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["file", "kind", "status", "rows_checked", "matched_hunt_codes", "rows_changed", "changed_cells"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    lines = [
        "# 2025 Draw-Results Permit Promotion",
        "",
        f"Generated UTC: {summary['generated_at_utc']}",
        f"Source file: `{summary['source_file']}`",
        f"Source rows used: `{summary['source_rows_used']}`",
        f"Source hunt codes: `{summary['source_hunt_codes']}`",
        f"Source hunt codes with nonzero total: `{summary['source_hunt_codes_with_nonzero_total']}`",
        f"Draw-field total mismatch count: `{summary['draw_field_total_mismatch_count']}`",
        f"Files written: `{summary['files_written']}`",
        "",
        "## Spot Checks",
        "",
        "| Hunt code | Res | NR | Total | Source files |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in summary["spot_checks"]:
        lines.append(f"| {row['hunt_code']} | {row['permits_2025_res']} | {row['permits_2025_nr']} | {row['permits_2025_total']} | {row['source_files']} |")
    lines.extend(["", "## Files", "", "| File | Matched codes | Rows changed | Changed cells |", "| --- | ---: | ---: | ---: |"])
    for result in results:
        lines.append(f"| {result['file']} | {result.get('matched_hunt_codes', 0)} | {result.get('rows_changed', 0)} | {result.get('changed_cells', 0)} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    source, metadata = build_source()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [patch_csv(path, source) for path in CSV_TARGETS]
    results.extend(patch_json(path, source) for path in JSON_TARGETS)
    summary = write_reports(results, source, metadata)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))
    return 1 if summary["draw_field_total_mismatch_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
