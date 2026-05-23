"""Promote canonical 2025 draw-result permit fields into runtime surfaces.

The canonical catalog already carries explicit 2025 draw-result permit totals
(`permits_2025_draw_*`). This script copies those fields into DATABASE.csv and
runtime/feed artifacts without writing ambiguous legacy year aliases.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_JSON = ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.json"
OUT_DIR = ROOT / "processed_data"
REPORT_JSON = OUT_DIR / "permits_2025_draw_field_promotion_report.json"
REPORT_CSV = OUT_DIR / "permits_2025_draw_field_promotion_report.csv"
REPORT_MD = OUT_DIR / "permits_2025_draw_field_promotion_report.md"

PROMOTED_FIELDS = [
    "permits_2025_draw_res",
    "permits_2025_draw_nr",
    "permits_2025_draw_total",
    "draw_2025_bg_pdf_page",
    "draw_2025_bg_report_page",
    "draw_2025_type",
]

TARGETS = [
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv",
    ROOT / "processed_data" / "hunt_master_enriched.csv",
    ROOT / "processed_data" / "hunt_unit_reference_linked.csv",
    ROOT / "processed_data" / "point_ladder_view.csv",
    ROOT / "processed_data" / "draw_reality_engine.csv",
    ROOT / "processed_data" / "draw_reality_engine_predictive_v2.csv",
    ROOT / "processed_data" / "ml_draw_predictions_v1.csv",
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.csv",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "hunt-master-canonical-2026.json",
    ROOT / "canonical" / "hunt-planner-2026.json",
    ROOT / "generated" / "pages" / "hunt-planner.json",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.json",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.json",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text in {"", "-", "–", "—", "None", "null"}:
        return ""
    return text


def code_of(row: dict[str, Any]) -> str:
    return clean(row.get("hunt_code") or row.get("huntCode") or row.get("code")).upper()


def load_source() -> dict[str, dict[str, str]]:
    data = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    rows = data.get("hunt_catalog") if isinstance(data, dict) else data
    source: dict[str, dict[str, str]] = {}
    for row in rows:
        code = code_of(row)
        if not code:
            continue
        values = {field: clean(row.get(field)) for field in PROMOTED_FIELDS}
        if not any(values[field] for field in ("permits_2025_draw_res", "permits_2025_draw_nr", "permits_2025_draw_total")):
            continue
        values["permits_2025_draw_source"] = "canonical_2026_source_of_truth_draw_results"
        source[code] = values
    return source


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def insert_fields(fields: list[str], new_fields: list[str]) -> list[str]:
    out = list(fields)
    insert_after = None
    if insert_after is None:
        for candidate in ("permits_2025_total", "permits_2026_total", "hunt_type", "hunt_name"):
            if candidate in out:
                insert_after = candidate
                break
    index = out.index(insert_after) + 1 if insert_after in out else len(out)
    for field in new_fields:
        if field not in out:
            out.insert(index, field)
            index += 1
    return out


def patch_row(
    row: dict[str, Any],
    source_values: dict[str, str],
) -> int:
    changed = 0
    for field in [*PROMOTED_FIELDS, "permits_2025_draw_source"]:
        value = source_values.get(field, "")
        if clean(row.get(field)) != value:
            row[field] = value
            changed += 1
    return changed


def patch_csv(path: Path, source: dict[str, dict[str, str]]) -> dict[str, Any]:
    rel = path.relative_to(ROOT).as_posix()
    fields, rows = read_csv(path)
    fieldnames = insert_fields(fields, [*PROMOTED_FIELDS, "permits_2025_draw_source"])
    matched_codes: set[str] = set()
    changed_cells = 0
    rows_changed = 0
    for row in rows:
        for field in fieldnames:
            row.setdefault(field, "")
        code = code_of(row)
        if code not in source:
            continue
        matched_codes.add(code)
        row_changes = patch_row(row, source[code])
        if row_changes:
            rows_changed += 1
            changed_cells += row_changes
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return {
        "file": rel,
        "kind": "csv",
        "rows_checked": len(rows),
        "matched_hunt_codes": len(matched_codes),
        "rows_changed": rows_changed,
        "changed_cells": changed_cells,
        "status": "written",
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
    rel = path.relative_to(ROOT).as_posix()
    data = json.loads(path.read_text(encoding="utf-8"))
    rows, container = json_rows(data)
    matched_codes: set[str] = set()
    changed_cells = 0
    rows_changed = 0
    for row in rows:
        code = code_of(row)
        if code not in source:
            continue
        matched_codes.add(code)
        row_changes = patch_row(row, source[code])
        if row_changes:
            rows_changed += 1
            changed_cells += row_changes
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "file": rel,
        "kind": "json",
        "container": container,
        "rows_checked": len(rows),
        "matched_hunt_codes": len(matched_codes),
        "rows_changed": rows_changed,
        "changed_cells": changed_cells,
        "status": "written",
    }


def spot_check(path: Path, code: str) -> dict[str, str]:
    if path.suffix.lower() == ".csv":
        _, rows = read_csv(path)
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows, _ = json_rows(data)
    for row in rows:
        if code_of(row) == code:
            return {
                "file": path.relative_to(ROOT).as_posix(),
                "hunt_code": code,
                "permits_2025_draw_res": clean(row.get("permits_2025_draw_res")),
                "permits_2025_draw_nr": clean(row.get("permits_2025_draw_nr")),
                "permits_2025_draw_total": clean(row.get("permits_2025_draw_total")),
                "draw_2025_bg_report_page": clean(row.get("draw_2025_bg_report_page")),
            }
    return {"file": path.relative_to(ROOT).as_posix(), "hunt_code": code, "status": "missing"}


def write_reports(results: list[dict[str, Any]], source: dict[str, dict[str, str]]) -> dict[str, Any]:
    status_counts = Counter(result["status"] for result in results)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": SOURCE_JSON.relative_to(ROOT).as_posix(),
        "source_hunt_codes_with_2025_draw_permits": len(source),
        "files_written": len([result for result in results if result["status"] == "written"]),
        "total_rows_changed": sum(int(result.get("rows_changed", 0)) for result in results),
        "total_changed_cells": sum(int(result.get("changed_cells", 0)) for result in results),
        "status_counts": dict(sorted(status_counts.items())),
        "results": results,
        "db1002_spot_checks": [
            spot_check(ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv", "DB1002"),
            spot_check(ROOT / "processed_data" / "hunt_master_enriched.csv", "DB1002"),
            spot_check(ROOT / "processed_data" / "point_ladder_view.csv", "DB1002"),
            spot_check(ROOT / "canonical" / "hunt-planner-2026.json", "DB1002"),
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with REPORT_CSV.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "file",
            "kind",
            "status",
            "rows_checked",
            "matched_hunt_codes",
            "rows_changed",
            "changed_cells",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    lines = [
        "# 2025 Draw Permit Field Promotion Report",
        "",
        f"Generated UTC: {summary['generated_at_utc']}",
        f"Source hunt codes with explicit 2025 draw permits: {summary['source_hunt_codes_with_2025_draw_permits']}",
        f"Files written: {summary['files_written']}",
        f"Rows changed: {summary['total_rows_changed']}",
        f"Changed cells: {summary['total_changed_cells']}",
        "",
        "## DB1002 Spot Check",
        "",
        "| File | permits_2025_draw_res | permits_2025_draw_nr | permits_2025_draw_total | report page |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["db1002_spot_checks"]:
        lines.append(
            f"| {row['file']} | {row.get('permits_2025_draw_res', '')} | {row.get('permits_2025_draw_nr', '')} | {row.get('permits_2025_draw_total', '')} | {row.get('draw_2025_bg_report_page', '')} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "| File | Matched codes | Rows changed | Changed cells |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for result in results:
        lines.append(
            f"| {result['file']} | {result.get('matched_hunt_codes', 0)} | {result.get('rows_changed', 0)} | {result.get('changed_cells', 0)} |"
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    source = load_source()
    results: list[dict[str, Any]] = []
    for path in TARGETS:
        if not path.exists():
            results.append(
                {
                    "file": path.relative_to(ROOT).as_posix(),
                    "kind": path.suffix.lower().lstrip("."),
                    "status": "missing",
                    "rows_checked": 0,
                    "matched_hunt_codes": 0,
                    "rows_changed": 0,
                    "changed_cells": 0,
                }
            )
            continue
        if path.suffix.lower() == ".csv":
            results.append(patch_csv(path, source))
        elif path.suffix.lower() == ".json":
            results.append(patch_json(path, source))
    summary = write_reports(results, source)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
