"""Remove empty database/catalog columns that carry no active value."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DROP_FIELDS = ["", "draw_2025_species_section"]
CSV_TARGETS = [
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv",
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
REPORT_JSON = ROOT / "processed_data" / "empty_database_column_removal_report.json"
REPORT_CSV = ROOT / "processed_data" / "empty_database_column_removal_report.csv"
REPORT_MD = ROOT / "processed_data" / "empty_database_column_removal_report.md"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def patch_csv(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"file": rel(path), "kind": "csv", "status": "missing", "rows_checked": 0, "blank_rows_removed": 0, "columns_removed": 0, "removed_fields": ""}
    fields, rows = read_csv(path)
    blank_rows = [row for row in rows if not any(clean(value) for value in row.values())]
    rows = [row for row in rows if any(clean(value) for value in row.values())]
    removed = []
    for field in DROP_FIELDS:
        if field in fields:
            nonblank = sum(1 for row in rows if clean(row.get(field)))
            if nonblank == 0:
                removed.append(field)
    if removed or blank_rows:
        next_fields = [field for field in fields if field not in removed]
        write_csv(path, next_fields, rows)
    return {
        "file": rel(path),
        "kind": "csv",
        "status": "cleaned" if removed or blank_rows else "no_empty_columns_or_rows",
        "rows_checked": len(rows) + len(blank_rows),
        "blank_rows_removed": len(blank_rows),
        "columns_removed": len(removed),
        "removed_fields": "|".join(field or "<blank_header>" for field in removed),
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


def patch_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"file": rel(path), "kind": "json", "status": "missing", "rows_checked": 0, "blank_rows_removed": 0, "columns_removed": 0, "removed_fields": ""}
    data = json.loads(path.read_text(encoding="utf-8"))
    rows, container = json_rows(data)
    removed_count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        for field in DROP_FIELDS:
            if field in row and not clean(row.get(field)):
                del row[field]
                removed_count += 1
    if removed_count:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "file": rel(path),
        "kind": "json",
        "container": container,
        "status": "cleaned" if removed_count else "no_empty_keys",
        "rows_checked": len(rows),
        "blank_rows_removed": 0,
        "columns_removed": removed_count,
        "removed_fields": "draw_2025_species_section" if removed_count else "",
    }


def database_column_check() -> dict[str, Any]:
    fields, rows = read_csv(CSV_TARGETS[0])
    return {
        "database_rows": len(rows),
        "database_unique_hunt_codes": len({clean(row.get("hunt_code")) for row in rows if clean(row.get("hunt_code"))}),
        "blank_header_count": fields.count(""),
        "has_draw_2025_species_section": "draw_2025_species_section" in fields,
        "fully_blank_rows": sum(1 for row in rows if not any(clean(value) for value in row.values())),
        "missing_hunt_code_nonblank_rows": sum(1 for row in rows if not clean(row.get("hunt_code")) and any(clean(value) for value in row.values())),
    }


def write_reports(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "drop_fields": ["<blank_header>", "draw_2025_species_section"],
        "files_checked": len(results),
        "files_cleaned": sum(1 for row in results if row["status"] == "cleaned"),
        "total_columns_or_keys_removed": sum(int(row["columns_removed"]) for row in results),
        "total_blank_rows_removed": sum(int(row["blank_rows_removed"]) for row in results),
        "database_column_check": database_column_check(),
        "results": results,
    }
    REPORT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with REPORT_CSV.open("w", newline="", encoding="utf-8") as handle:
        fields = ["file", "kind", "status", "rows_checked", "blank_rows_removed", "columns_removed", "removed_fields"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    lines = [
        "# Empty Database Column Removal",
        "",
        f"Generated UTC: {summary['generated_at_utc']}",
        f"Files cleaned: `{summary['files_cleaned']}`",
        f"Columns/JSON keys removed: `{summary['total_columns_or_keys_removed']}`",
        f"Blank rows removed: `{summary['total_blank_rows_removed']}`",
        "",
        "## DATABASE.csv Check",
        "",
        f"- Rows: `{summary['database_column_check']['database_rows']}`",
        f"- Unique hunt codes: `{summary['database_column_check']['database_unique_hunt_codes']}`",
        f"- Blank header count: `{summary['database_column_check']['blank_header_count']}`",
        f"- Has `draw_2025_species_section`: `{summary['database_column_check']['has_draw_2025_species_section']}`",
        f"- Fully blank rows: `{summary['database_column_check']['fully_blank_rows']}`",
        f"- Nonblank rows missing hunt code: `{summary['database_column_check']['missing_hunt_code_nonblank_rows']}`",
        "",
        "## Files",
        "",
        "| File | Status | Blank rows removed | Removed count | Removed fields |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in results:
        lines.append(f"| {row['file']} | {row['status']} | {row['blank_rows_removed']} | {row['columns_removed']} | {row['removed_fields']} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    results = [patch_csv(path) for path in CSV_TARGETS]
    results.extend(patch_json(path) for path in JSON_TARGETS)
    summary = write_reports(results)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))
    check = summary["database_column_check"]
    return 1 if check["blank_header_count"] or check["has_draw_2025_species_section"] or check["fully_blank_rows"] or check["missing_hunt_code_nonblank_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
