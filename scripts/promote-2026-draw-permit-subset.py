"""Create and promote the explicit 2026 draw-permit subset.

The 2025 database already carries `permits_2025_draw_*` as a narrower draw
subset. 2026 had the same idea implicitly through runtime quota fields such as
`public_permits_2026`, but DATABASE.csv did not carry a matching explicit
`permits_2026_draw_*` family.

This script uses the current draw prediction surface only to identify which
hunt codes feed the draw engine. The permit numbers themselves come from the
canonical DATABASE.csv 2026 permit/allotment fields.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
DRAW_ENGINE = ROOT / "processed_data" / "ml_draw_predictions_v1.csv"
OUT_DIR = ROOT / "data_truth" / "comparison_outputs" / "validation"
SUBSET_CSV = OUT_DIR / "permits_2026_draw_subset.csv"
SUMMARY_JSON = OUT_DIR / "permits_2026_draw_subset_summary.json"
REPORT_MD = ROOT / "processed_data" / "permits_2026_draw_subset.md"
PROMOTION_REPORT_JSON = ROOT / "processed_data" / "permits_2026_draw_field_promotion_report.json"
PROMOTION_REPORT_CSV = ROOT / "processed_data" / "permits_2026_draw_field_promotion_report.csv"

DRAW_FIELDS = [
    "permits_2026_draw_res",
    "permits_2026_draw_nr",
    "permits_2026_draw_total",
    "permits_2026_draw_source",
    "draw_2026_system_type",
]

DEPRECATED_FIELDS = ["draw_2026_permit_family"]

TARGETS = [
    DATABASE,
    ROOT / "processed_data" / "hunt_master_enriched_2026_draw_subset.csv",
    ROOT / "processed_data" / "hunt_unit_reference_linked.csv",
    ROOT / "processed_data" / "point_ladder_view.csv",
    ROOT / "processed_data" / "draw_reality_engine.csv",
    ROOT / "processed_data" / "draw_reality_engine_predictive_v2.csv",
    ROOT / "processed_data" / "ml_draw_predictions_v1.csv",
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.csv",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.csv",
]

EXCLUDED_DRAW_SYSTEM_TYPES = {"MOUNTAIN_LION_DRAW"}


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    if text in {"", "-", "–", "—", "None", "none", "null", "NULL"}:
        return ""
    return text


def code_of(row: dict[str, Any]) -> str:
    return clean(row.get("hunt_code") or row.get("huntCode") or row.get("code")).upper()


def number_text(value: object) -> str:
    text = clean(value).replace(",", "")
    if not text:
        return ""
    try:
        numeric = float(text)
    except ValueError:
        return ""
    if numeric < 0:
        return ""
    return str(int(numeric)) if numeric.is_integer() else str(numeric)


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


def insert_fields(fields: list[str]) -> list[str]:
    out = [field for field in fields if field not in DEPRECATED_FIELDS]
    anchor = None
    for candidate in ("permits_2026_source", "permit_allotment_2026_source", "permits_2026_total", "hunt_type"):
        if candidate in out:
            anchor = candidate
            break
    index = out.index(anchor) + 1 if anchor else len(out)
    for field in DRAW_FIELDS:
        if field not in out:
            out.insert(index, field)
            index += 1
    return out


def load_draw_engine_codes() -> dict[str, str]:
    _, rows = read_csv(DRAW_ENGINE)
    draw_system_by_code: dict[str, str] = {}
    for row in rows:
        code = code_of(row)
        draw_type = clean(row.get("draw_system_type"))
        if not code or not draw_type or draw_type in EXCLUDED_DRAW_SYSTEM_TYPES:
            continue
        draw_system_by_code.setdefault(code, draw_type)
    return draw_system_by_code


def choose_database_values(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    permit_total = number_text(row.get("permits_2026_total"))
    allotment_total = number_text(row.get("permit_allotment_2026_total"))
    if permit_total:
        return (
            number_text(row.get("permits_2026_res")),
            number_text(row.get("permits_2026_nr")),
            permit_total,
            clean(row.get("permits_2026_source")),
            "permits_2026",
        )
    if allotment_total:
        return (
            number_text(row.get("permit_allotment_2026_res")),
            number_text(row.get("permit_allotment_2026_nr")),
            allotment_total,
            clean(row.get("permit_allotment_2026_source")),
            "permit_allotment_2026",
        )
    return "", "", "", "", ""


def build_subset() -> tuple[dict[str, dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    draw_system_by_code = load_draw_engine_codes()
    _, database_rows = read_csv(DATABASE)
    subset: dict[str, dict[str, str]] = {}
    validation_rows: list[dict[str, str]] = []
    skipped_engine_codes: list[str] = []
    nonnumeric_database_totals: list[str] = []

    for row in database_rows:
        code = code_of(row)
        if code not in draw_system_by_code:
            continue
        res, nr, total, source, source_field_family = choose_database_values(row)
        if not total:
            skipped_engine_codes.append(code)
            if clean(row.get("permits_2026_total")) or clean(row.get("permit_allotment_2026_total")):
                nonnumeric_database_totals.append(code)
            continue
        values = {
            "permits_2026_draw_res": res,
            "permits_2026_draw_nr": nr,
            "permits_2026_draw_total": total,
            "permits_2026_draw_source": source,
            "draw_2026_system_type": draw_system_by_code[code],
        }
        subset[code] = values
        validation_rows.append(
            {
                "hunt_code": code,
                "boundary_id": row.get("boundary_id", ""),
                "hunt_name": row.get("hunt_name", ""),
                "species": row.get("species", ""),
                "sex_type": row.get("sex_type", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "season": row.get("season", ""),
                **values,
                "source_field_family": source_field_family,
            }
        )

    engine_codes_missing_database = sorted(set(draw_system_by_code) - {code_of(row) for row in database_rows})
    summary = {
        "artifact": "permits_2026_draw_subset",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "database_path": DATABASE.relative_to(ROOT).as_posix(),
        "draw_engine_path": DRAW_ENGINE.relative_to(ROOT).as_posix(),
        "draw_engine_hunt_code_count": len(draw_system_by_code),
        "subset_hunt_code_count": len(subset),
        "skipped_engine_codes_without_numeric_2026_total_count": len(skipped_engine_codes),
        "skipped_engine_codes_without_numeric_2026_total": sorted(skipped_engine_codes)[:200],
        "engine_codes_missing_database_count": len(engine_codes_missing_database),
        "engine_codes_missing_database": engine_codes_missing_database[:200],
        "nonnumeric_database_totals_count": len(nonnumeric_database_totals),
        "nonnumeric_database_totals": sorted(nonnumeric_database_totals)[:200],
        "draw_system_type_counts": dict(sorted(Counter(row["draw_2026_system_type"] for row in validation_rows).items())),
        "species_counts": dict(sorted(Counter(row["species"] for row in validation_rows).items())),
        "hunt_type_counts": dict(sorted(Counter(row["hunt_type"] for row in validation_rows).items())),
        "source_field_family_counts": dict(sorted(Counter(row["source_field_family"] for row in validation_rows).items())),
        "guardrail": "Subset membership comes from draw_system_type; permit values are copied from DATABASE.csv 2026 permit/allotment fields only.",
    }
    return subset, validation_rows, summary


def patch_row(row: dict[str, Any], source_values: dict[str, str] | None) -> int:
    changed = 0
    for field in DRAW_FIELDS:
        value = clean(source_values.get(field)) if source_values else ""
        if clean(row.get(field)) != value:
            row[field] = value
            changed += 1
    return changed


def patch_csv(path: Path, subset: dict[str, dict[str, str]]) -> dict[str, Any]:
    rel = path.relative_to(ROOT).as_posix()
    if not path.exists():
        return {
            "file": rel,
            "status": "missing",
            "rows_checked": 0,
            "matched_hunt_codes": 0,
            "rows_changed": 0,
            "changed_cells": 0,
        }
    if path.read_text(encoding="utf-8", errors="ignore").startswith("version https://git-lfs.github.com/spec/v1"):
        return {
            "file": rel,
            "status": "skipped_lfs_pointer",
            "rows_checked": 0,
            "matched_hunt_codes": 0,
            "rows_changed": 0,
            "changed_cells": 0,
        }
    fields, rows = read_csv(path)
    fieldnames = insert_fields(fields)
    matched: set[str] = set()
    changed_cells = 0
    rows_changed = 0
    for row in rows:
        for field in fieldnames:
            row.setdefault(field, "")
        code = code_of(row)
        values = subset.get(code)
        if values:
            matched.add(code)
        row_changes = patch_row(row, values)
        if row_changes:
            rows_changed += 1
            changed_cells += row_changes
    write_csv(path, fieldnames, rows)
    return {
        "file": rel,
        "status": "written",
        "rows_checked": len(rows),
        "matched_hunt_codes": len(matched),
        "rows_changed": rows_changed,
        "changed_cells": changed_cells,
    }


def spot_check(path: Path, code: str) -> dict[str, str]:
    if not path.exists():
        return {"file": path.relative_to(ROOT).as_posix(), "hunt_code": code, "status": "missing_file"}
    _, rows = read_csv(path)
    for row in rows:
        if code_of(row) == code:
            return {
                "file": path.relative_to(ROOT).as_posix(),
                "hunt_code": code,
                "permits_2026_draw_res": row.get("permits_2026_draw_res", ""),
                "permits_2026_draw_nr": row.get("permits_2026_draw_nr", ""),
                "permits_2026_draw_total": row.get("permits_2026_draw_total", ""),
                "permits_2026_draw_source": row.get("permits_2026_draw_source", ""),
                "draw_2026_system_type": row.get("draw_2026_system_type", ""),
            }
    return {"file": path.relative_to(ROOT).as_posix(), "hunt_code": code, "status": "missing_code"}


def write_reports(
    subset: dict[str, dict[str, str]],
    validation_rows: list[dict[str, str]],
    summary: dict[str, Any],
    promotion_results: list[dict[str, Any]],
) -> None:
    detail_fields = [
        "hunt_code",
        "boundary_id",
        "hunt_name",
        "species",
        "sex_type",
        "weapon",
        "hunt_type",
        "season",
        *DRAW_FIELDS,
        "source_field_family",
    ]
    write_csv(SUBSET_CSV, detail_fields, validation_rows)
    promotion_summary = {
        **summary,
        "outputs": {
            "subset_csv": SUBSET_CSV.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "report_md": REPORT_MD.relative_to(ROOT).as_posix(),
            "promotion_report_json": PROMOTION_REPORT_JSON.relative_to(ROOT).as_posix(),
            "promotion_report_csv": PROMOTION_REPORT_CSV.relative_to(ROOT).as_posix(),
        },
        "promotion_results": promotion_results,
        "files_written": sum(1 for row in promotion_results if row["status"] == "written"),
        "total_rows_changed": sum(int(row.get("rows_changed", 0)) for row in promotion_results),
        "total_changed_cells": sum(int(row.get("changed_cells", 0)) for row in promotion_results),
        "spot_checks": [
            spot_check(DATABASE, "EB3022"),
            spot_check(DATABASE, "DB1002"),
            spot_check(DATABASE, "BI6528"),
            spot_check(DATABASE, "EA2012"),
            spot_check(DATABASE, "CG9999"),
            spot_check(ROOT / "processed_data" / "ml_draw_predictions_v1.csv", "EB3022"),
        ],
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    PROMOTION_REPORT_JSON.write_text(json.dumps(promotion_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(
        PROMOTION_REPORT_CSV,
        ["file", "status", "rows_checked", "matched_hunt_codes", "rows_changed", "changed_cells"],
        promotion_results,
    )

    lines = [
        "# 2026 Draw Permit Subset",
        "",
        f"- Generated UTC: `{summary['generated_at_utc']}`",
        f"- Draw-engine hunt codes: `{summary['draw_engine_hunt_code_count']}`",
        f"- Promoted 2026 draw-permit subset codes: `{summary['subset_hunt_code_count']}`",
        f"- Engine codes missing DATABASE: `{summary['engine_codes_missing_database_count']}`",
        f"- Engine codes without numeric 2026 total: `{summary['skipped_engine_codes_without_numeric_2026_total_count']}`",
        "",
        "## Draw System Type Counts",
        "",
    ]
    for draw_type, count in summary["draw_system_type_counts"].items():
        lines.append(f"- `{draw_type}`: `{count}`")
    lines.extend(
        [
            "",
            "## Spot Checks",
            "",
            "| File | Hunt code | Res | NR | Total | Source | Draw type |",
            "| --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in promotion_summary["spot_checks"]:
        lines.append(
            "| {file} | {hunt_code} | {res} | {nr} | {total} | {source} | {draw_type} |".format(
                file=row.get("file", ""),
                hunt_code=row.get("hunt_code", ""),
                res=row.get("permits_2026_draw_res", ""),
                nr=row.get("permits_2026_draw_nr", ""),
                total=row.get("permits_2026_draw_total", ""),
                source=row.get("permits_2026_draw_source", ""),
                draw_type=row.get("draw_2026_system_type", ""),
            )
        )
    lines.extend(["", "## Promotion Targets", "", "| File | Matched codes | Rows changed | Changed cells |", "| --- | ---: | ---: | ---: |"])
    for result in promotion_results:
        lines.append(
            f"| {result['file']} | {result.get('matched_hunt_codes', 0)} | {result.get('rows_changed', 0)} | {result.get('changed_cells', 0)} |"
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    subset, validation_rows, summary = build_subset()
    promotion_results = [patch_csv(path, subset) for path in TARGETS]
    write_reports(subset, validation_rows, summary, promotion_results)
    print(json.dumps({key: value for key, value in summary.items() if not key.endswith("_codes")}, indent=2, sort_keys=True))
    return 1 if summary["engine_codes_missing_database_count"] or summary["nonnumeric_database_totals_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
