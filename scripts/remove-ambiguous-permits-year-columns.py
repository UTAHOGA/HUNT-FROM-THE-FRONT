"""Remove ambiguous permits_year_* aliases from active 2026 runtime surfaces.

The project now carries explicit permit-year fields:
- 2025 draw-result permit counts: permits_2025_draw_*
- 2026 active allotments: permits_2026_* and permit_allotment_2026_*

This cleanup keeps those explicit fields and drops the generic permits_year_*
columns from publish-facing current-year CSV/JSON data.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DROP_FIELDS = ["permits_year_res", "permits_year_nr", "permits_year_total"]
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
JSON_LIST_CLEANUP_TARGETS = [
    ROOT / "generated" / "pages" / "hunt-research.json",
]
OUT_DIR = ROOT / "processed_data"
REPORT_JSON = OUT_DIR / "permits_year_column_removal_report.json"
REPORT_CSV = OUT_DIR / "permits_year_column_removal_report.csv"
REPORT_MD = OUT_DIR / "permits_year_column_removal_report.md"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def remove_from_lists(value: Any) -> tuple[Any, int]:
    removed = 0
    if isinstance(value, list):
        cleaned = []
        for item in value:
            if item in DROP_FIELDS:
                removed += 1
                continue
            next_item, next_removed = remove_from_lists(item)
            removed += next_removed
            cleaned.append(next_item)
        return cleaned, removed
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            next_item, next_removed = remove_from_lists(item)
            removed += next_removed
            out[key] = next_item
        return out, removed
    return value, removed


def patch_csv(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "file": rel(path),
            "kind": "csv",
            "status": "missing",
            "rows_checked": 0,
            "columns_removed": 0,
            "removed_fields": "",
            "written": False,
        }
    fieldnames, rows = read_csv(path)
    removed = [field for field in DROP_FIELDS if field in fieldnames]
    if not removed:
        return {
            "file": rel(path),
            "kind": "csv",
            "status": "no_ambiguous_columns",
            "rows_checked": len(rows),
            "columns_removed": 0,
            "removed_fields": "",
            "written": False,
        }
    next_fieldnames = [field for field in fieldnames if field not in DROP_FIELDS]
    write_csv(path, next_fieldnames, rows)
    return {
        "file": rel(path),
        "kind": "csv",
        "status": "columns_removed",
        "rows_checked": len(rows),
        "columns_removed": len(removed),
        "removed_fields": "|".join(removed),
        "written": True,
    }


def patch_json_lists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "file": rel(path),
            "kind": "json",
            "status": "missing",
            "rows_checked": 0,
            "columns_removed": 0,
            "removed_fields": "",
            "written": False,
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    cleaned, removed = remove_from_lists(data)
    if removed:
        path.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
    return {
        "file": rel(path),
        "kind": "json",
        "status": "list_references_removed" if removed else "no_ambiguous_references",
        "rows_checked": 0,
        "columns_removed": removed,
        "removed_fields": "|".join(DROP_FIELDS) if removed else "",
        "written": bool(removed),
    }


def db1002_spot_check() -> dict[str, str]:
    _, rows = read_csv(CSV_TARGETS[0])
    row = next((item for item in rows if item.get("hunt_code") == "DB1002"), {})
    return {
        "hunt_code": "DB1002",
        "permits_2025_draw_res": row.get("permits_2025_draw_res", ""),
        "permits_2025_draw_nr": row.get("permits_2025_draw_nr", ""),
        "permits_2025_draw_total": row.get("permits_2025_draw_total", ""),
        "permit_allotment_2026_res": row.get("permit_allotment_2026_res", ""),
        "permit_allotment_2026_nr": row.get("permit_allotment_2026_nr", ""),
        "permit_allotment_2026_total": row.get("permit_allotment_2026_total", ""),
    }


def write_reports(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "removed_fields": DROP_FIELDS,
        "target_count": len(results),
        "files_written": sum(1 for row in results if row["written"]),
        "total_columns_or_references_removed": sum(int(row["columns_removed"]) for row in results),
        "db1002_spot_check": db1002_spot_check(),
        "results": results,
    }
    REPORT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with REPORT_CSV.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["file", "kind", "status", "rows_checked", "columns_removed", "removed_fields", "written"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    lines = [
        "# Ambiguous Permit-Year Column Removal",
        "",
        f"Generated UTC: {summary['generated_at_utc']}",
        f"Removed fields: `{', '.join(DROP_FIELDS)}`",
        f"Files written: `{summary['files_written']}`",
        f"Total columns/list references removed: `{summary['total_columns_or_references_removed']}`",
        "",
        "## DB1002 Explicit Field Check",
        "",
        f"- 2025 draw-result permits: `{summary['db1002_spot_check']['permits_2025_draw_res']} / {summary['db1002_spot_check']['permits_2025_draw_nr']} / {summary['db1002_spot_check']['permits_2025_draw_total']}`",
        f"- 2026 allotment permits: `{summary['db1002_spot_check']['permit_allotment_2026_res']} / {summary['db1002_spot_check']['permit_allotment_2026_nr']} / {summary['db1002_spot_check']['permit_allotment_2026_total']}`",
        "",
        "## Files",
        "",
        "| File | Status | Removed | Written |",
        "| --- | --- | ---: | --- |",
    ]
    for row in results:
        lines.append(f"| {row['file']} | {row['status']} | {row['columns_removed']} | {row['written']} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [patch_csv(path) for path in CSV_TARGETS]
    results.extend(patch_json_lists(path) for path in JSON_LIST_CLEANUP_TARGETS)
    summary = write_reports(results)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
