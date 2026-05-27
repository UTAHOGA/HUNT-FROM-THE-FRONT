from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.utah_draw_predictive.classifier import classify_draw_system_type, classification_reason, resolve_algorithm_status

DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
HUNT_MASTER = ROOT / "processed_data" / "hunt_master_enriched.csv"

DETAIL_CSV = ROOT / "data_truth" / "comparison_outputs" / "validation" / "hunt_master_enriched_hunt_class_routing_2026.csv"
SUMMARY_JSON = ROOT / "data_truth" / "comparison_outputs" / "validation" / "hunt_master_enriched_hunt_class_routing_2026_summary.json"
REPORT_MD = ROOT / "processed_data" / "hunt_master_enriched_hunt_class_routing_2026.md"

PROMOTED_SELECTOR_FIELDS = ["species", "sex_type", "hunt_class"]
PROMOTED_ROUTING_FIELDS = ["draw_2026_system_type", "draw_system_type", "algorithm_status", "draw_routing_reason"]
PROTECTED_NUMERIC_PREFIXES = ("permits_", "permit_allotment_", "public_permits_", "max_point_permits_", "random_permits_")


def clean(value: object) -> str:
    return str(value or "").strip()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def insert_after(fieldnames: list[str], field: str, anchor: str) -> list[str]:
    if field in fieldnames:
        return fieldnames
    out = list(fieldnames)
    if anchor in out:
        out.insert(out.index(anchor) + 1, field)
    else:
        out.append(field)
    return out


def target_fieldnames(fieldnames: list[str]) -> list[str]:
    out = list(fieldnames)
    out = insert_after(out, "species", "hunt_name")
    out = insert_after(out, "sex_type", "species")
    out = insert_after(out, "hunt_class", "weapon")
    out = insert_after(out, "draw_2026_system_type", "data_status")
    out = insert_after(out, "draw_system_type", "draw_2026_system_type")
    out = insert_after(out, "algorithm_status", "draw_system_type")
    out = insert_after(out, "draw_routing_reason", "algorithm_status")
    return out


def code_of(row: dict[str, str]) -> str:
    return clean(row.get("hunt_code")).upper()


def protected_snapshot(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], tuple[str, ...]]:
    protected_fields = [
        field
        for field in rows[0].keys()
        if field.startswith(PROTECTED_NUMERIC_PREFIXES) or field in {"odds_2025", "odds_2026_projected"}
    ] if rows else []
    snapshot: dict[tuple[str, str, str, str], tuple[str, ...]] = {}
    for index, row in enumerate(rows):
        key = (str(index), code_of(row), clean(row.get("residency")), clean(row.get("points")))
        snapshot[key] = tuple(clean(row.get(field)) for field in protected_fields)
    return snapshot


def load_database_map() -> dict[str, dict[str, str]]:
    _, rows = read_csv(DATABASE)
    return {code_of(row): row for row in rows if code_of(row)}


def main() -> int:
    db_by_code = load_database_map()
    original_fields, rows = read_csv(HUNT_MASTER)
    original_row_count = len(rows)
    original_unique_codes = len({code_of(row) for row in rows if code_of(row)})
    original_snapshot = protected_snapshot(rows)
    fieldnames = target_fieldnames(original_fields)

    changed_rows = 0
    selector_cells_changed = 0
    routing_cells_changed = 0
    detail_rows: list[dict[str, str]] = []
    route_counts: Counter[str] = Counter()
    algorithm_counts: Counter[str] = Counter()

    for row in rows:
        for field in fieldnames:
            row.setdefault(field, "")
        code = code_of(row)
        db_row = db_by_code.get(code, {})
        changed = False

        for field in PROMOTED_SELECTOR_FIELDS:
            value = clean(db_row.get(field))
            if value and clean(row.get(field)) != value:
                row[field] = value
                selector_cells_changed += 1
                changed = True

        classification_row = dict(row)
        for field in PROMOTED_SELECTOR_FIELDS:
            if not clean(classification_row.get(field)) and clean(db_row.get(field)):
                classification_row[field] = clean(db_row.get(field))

        draw_system_type = classify_draw_system_type(classification_row)
        algorithm_status = resolve_algorithm_status(classification_row, draw_system_type)
        reason = classification_reason(classification_row, draw_system_type, algorithm_status)
        route_values = {
            "draw_2026_system_type": draw_system_type,
            "draw_system_type": draw_system_type,
            "algorithm_status": algorithm_status,
            "draw_routing_reason": reason,
        }
        for field, value in route_values.items():
            if clean(row.get(field)) != value:
                row[field] = value
                routing_cells_changed += 1
                changed = True

        if changed:
            changed_rows += 1
        route_counts[draw_system_type] += 1
        algorithm_counts[algorithm_status] += 1

        if code in {"EB1007", "EB1011", "DB1501", "EA1239"}:
            detail_rows.append(
                {
                    "hunt_code": code,
                    "hunt_name": clean(row.get("hunt_name")),
                    "species": clean(row.get("species")),
                    "sex_type": clean(row.get("sex_type")),
                    "hunt_type": clean(row.get("hunt_type")),
                    "weapon": clean(row.get("weapon")),
                    "hunt_class": clean(row.get("hunt_class")),
                    "draw_2026_system_type": clean(row.get("draw_2026_system_type")),
                    "draw_system_type": clean(row.get("draw_system_type")),
                    "algorithm_status": clean(row.get("algorithm_status")),
                    "draw_routing_reason": clean(row.get("draw_routing_reason")),
                    "residency": clean(row.get("residency")),
                    "points": clean(row.get("points")),
                }
            )

    after_snapshot = protected_snapshot(rows)
    protected_numeric_cells_changed = sum(1 for key, before in original_snapshot.items() if after_snapshot.get(key) != before)
    if protected_numeric_cells_changed:
        raise RuntimeError(f"Protected numeric permit/projection cells changed: {protected_numeric_cells_changed}")

    write_csv(HUNT_MASTER, fieldnames, rows)
    DETAIL_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_csv(
        DETAIL_CSV,
        [
            "hunt_code",
            "hunt_name",
            "species",
            "sex_type",
            "hunt_type",
            "weapon",
            "hunt_class",
            "draw_2026_system_type",
            "draw_system_type",
            "algorithm_status",
            "draw_routing_reason",
            "residency",
            "points",
        ],
        detail_rows,
    )

    summary = {
        "artifact": "hunt_master_enriched_hunt_class_routing_2026",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "hunt_master_path": str(HUNT_MASTER.relative_to(ROOT)).replace("\\", "/"),
        "database_path": str(DATABASE.relative_to(ROOT)).replace("\\", "/"),
        "row_count_before": original_row_count,
        "row_count_after": len(rows),
        "unique_hunt_codes_before": original_unique_codes,
        "unique_hunt_codes_after": len({code_of(row) for row in rows if code_of(row)}),
        "fields_added": [field for field in fieldnames if field not in original_fields],
        "selector_cells_changed": selector_cells_changed,
        "routing_cells_changed": routing_cells_changed,
        "rows_changed": changed_rows,
        "protected_numeric_cells_changed": protected_numeric_cells_changed,
        "draw_system_type_counts": dict(sorted(route_counts.items())),
        "algorithm_status_counts": dict(sorted(algorithm_counts.items())),
        "guardrail": "Main enriched rows are preserved. Selector/routing fields are appended or populated by hunt_code; protected numeric permit/projection cells are not changed.",
        "detail_csv": str(DETAIL_CSV.relative_to(ROOT)).replace("\\", "/"),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# Hunt Master Enriched Hunt Class Routing 2026",
                "",
                f"- Rows before: `{summary['row_count_before']}`",
                f"- Rows after: `{summary['row_count_after']}`",
                f"- Unique hunt codes after: `{summary['unique_hunt_codes_after']}`",
                f"- Fields added: `{', '.join(summary['fields_added'])}`",
                f"- Protected numeric cells changed: `{summary['protected_numeric_cells_changed']}`",
                f"- Rows with selector/routing changes: `{summary['rows_changed']}`",
                "",
                "This promotion keeps the main enriched file intact and adds the selector/routing fields needed by the hunt matrix and draw-engine dispatch.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
