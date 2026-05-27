"""Promote canonical hunt_class into active 2026 selection-matrix surfaces.

DWR-facing selection order for the hunt picker is:

    species -> sex_type -> hunt_type -> weapon -> hunt_class

`hunt_type` is the primary DWR hunt category. `hunt_class` is the user-facing
refinement layer after weapon selection, used only when it further diversifies
the resolved hunt set. `draw_2026_system_type` remains internal engine routing.
This script backfills hunt_class where active runtime/database files were
missing it and removes the duplicate `draw_2026_permit_family` column.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "utah" / "official_downloads_2026" / "hunt_master_canonical_2026.csv"
OUT_DIR = ROOT / "data_truth" / "comparison_outputs" / "validation"
DETAIL_CSV = OUT_DIR / "hunt_class_selection_matrix_2026.csv"
SUMMARY_JSON = OUT_DIR / "hunt_class_selection_matrix_2026_summary.json"
REPORT_MD = ROOT / "processed_data" / "hunt_class_selection_matrix_2026.md"

TARGETS = [
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv",
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.csv",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "processed_data" / "hunt_unit_reference_linked.csv",
    ROOT / "processed_data" / "point_ladder_view.csv",
    ROOT / "processed_data" / "draw_reality_engine.csv",
    ROOT / "processed_data" / "draw_reality_engine_predictive_v2.csv",
    ROOT / "processed_data" / "ml_draw_predictions_v1.csv",
    ROOT / "processed_data" / "hunt_master_enriched_2026_draw_subset.csv",
]

REMOVED_FIELDS = ["draw_2026_permit_family"]
PROMOTED_FIELDS = ["hunt_class"]


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    if text in {"", "-", "–", "—", "None", "none", "null", "NULL"}:
        return ""
    return text


def code_of(row: dict[str, Any]) -> str:
    return clean(row.get("hunt_code") or row.get("huntCode") or row.get("code")).upper()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [{key: clean(value) for key, value in row.items()} for row in reader]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_source() -> dict[str, str]:
    _, rows = read_csv(SOURCE)
    source: dict[str, str] = {}
    for row in rows:
        code = code_of(row)
        hunt_class = clean(row.get("hunt_class"))
        if code and hunt_class:
            source[code] = hunt_class
    return source


def insert_hunt_class(fields: list[str]) -> list[str]:
    out = [field for field in fields if field not in REMOVED_FIELDS]
    if "hunt_class" in out:
        return out
    anchor = None
    for candidate in ("hunt_type", "sex_type", "weapon", "hunt_name"):
        if candidate in out:
            anchor = candidate
            break
    index = out.index(anchor) + 1 if anchor else len(out)
    out.insert(index, "hunt_class")
    return out


def patch_target(path: Path, source: dict[str, str]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    rel = path.relative_to(ROOT).as_posix()
    if not path.exists():
        return {
            "file": rel,
            "status": "missing",
            "rows_checked": 0,
            "matched_hunt_codes": 0,
            "rows_changed": 0,
            "changed_cells": 0,
            "removed_duplicate_field": False,
        }, []
    if path.read_text(encoding="utf-8", errors="ignore").startswith("version https://git-lfs.github.com/spec/v1"):
        return {
            "file": rel,
            "status": "skipped_lfs_pointer",
            "rows_checked": 0,
            "matched_hunt_codes": 0,
            "rows_changed": 0,
            "changed_cells": 0,
            "removed_duplicate_field": False,
        }, []
    fields, rows = read_csv(path)
    fieldnames = insert_hunt_class(fields)
    removed_duplicate = any(field in fields for field in REMOVED_FIELDS)
    matched: set[str] = set()
    changed_cells = 0
    rows_changed = 0
    detail_rows: list[dict[str, str]] = []

    for row in rows:
        for field in fieldnames:
            row.setdefault(field, "")
        for field in REMOVED_FIELDS:
            row.pop(field, None)
        code = code_of(row)
        if code not in source:
            continue
        matched.add(code)
        previous = clean(row.get("hunt_class"))
        new_value = source[code]
        if previous != new_value:
            row["hunt_class"] = new_value
            changed_cells += 1
            rows_changed += 1
        if rel.endswith("DATABASE.csv"):
            detail_rows.append(
                {
                    "hunt_code": code,
                    "hunt_name": row.get("hunt_name", ""),
                    "species": row.get("species", ""),
                    "sex_type": row.get("sex_type", ""),
                    "hunt_class": row.get("hunt_class", ""),
                    "hunt_type": row.get("hunt_type", ""),
                    "weapon": row.get("weapon", ""),
                    "draw_2026_system_type": row.get("draw_2026_system_type", ""),
                }
            )

    write_csv(path, fieldnames, rows)
    return {
        "file": rel,
        "status": "written",
        "rows_checked": len(rows),
        "matched_hunt_codes": len(matched),
        "rows_changed": rows_changed,
        "changed_cells": changed_cells,
        "removed_duplicate_field": removed_duplicate,
    }, detail_rows


def main() -> int:
    source = load_source()
    results: list[dict[str, Any]] = []
    detail_rows: list[dict[str, str]] = []
    for path in TARGETS:
        result, details = patch_target(path, source)
        results.append(result)
        detail_rows.extend(details)

    database_details = [row for row in detail_rows if row.get("hunt_class")]
    summary = {
        "artifact": "hunt_class_selection_matrix_2026",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_hunt_code_count": len(source),
        "selection_matrix": ["species", "sex_type", "hunt_type", "weapon", "hunt_class"],
        "internal_engine_field": "draw_2026_system_type",
        "removed_duplicate_fields": REMOVED_FIELDS,
        "database_hunt_class_populated_count": len(database_details),
        "database_hunt_class_counts": dict(sorted(Counter(row["hunt_class"] for row in database_details).items())),
        "files_written": sum(1 for row in results if row["status"] == "written"),
        "results": results,
        "guardrail": "hunt_class is the user-facing selection class; draw_2026_system_type is internal engine routing and must not be exposed as a duplicate selector.",
    }

    write_csv(
        DETAIL_CSV,
        ["hunt_code", "hunt_name", "species", "sex_type", "hunt_class", "hunt_type", "weapon", "draw_2026_system_type"],
        sorted(detail_rows, key=lambda row: row["hunt_code"]),
    )
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# 2026 Hunt Class Selection Matrix",
        "",
        f"- Generated UTC: `{summary['generated_at_utc']}`",
        "- Selection order: `species -> sex_type -> hunt_type -> weapon -> hunt_class`",
        "- Internal engine route: `draw_2026_system_type`",
        "- Removed duplicate selector field: `draw_2026_permit_family`",
        f"- DATABASE hunt_class populated rows: `{summary['database_hunt_class_populated_count']}`",
        "",
        "## DATABASE Hunt Class Counts",
        "",
    ]
    for hunt_class, count in summary["database_hunt_class_counts"].items():
        lines.append(f"- `{hunt_class}`: `{count}`")
    lines.extend(["", "## Files", "", "| File | Matched codes | Rows changed | Duplicate field removed |", "| --- | ---: | ---: | --- |"])
    for result in results:
        lines.append(
            f"| {result['file']} | {result.get('matched_hunt_codes', 0)} | {result.get('rows_changed', 0)} | {result.get('removed_duplicate_field', False)} |"
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
