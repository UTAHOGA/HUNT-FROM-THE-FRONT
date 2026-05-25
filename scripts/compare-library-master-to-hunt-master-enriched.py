#!/usr/bin/env python3
"""Compare reconciled library-master rows to hunt_master_enriched runtime rows."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBRARY_RECONCILED = ROOT / "pipeline/RAW/hunt_unit_database/library-master.reconciled.csv"
HUNT_MASTER = ROOT / "processed_data/hunt_master_enriched.csv"
OUT_CSV = ROOT / "processed_data/library_master_vs_hunt_master_enriched.csv"
OUT_JSON = ROOT / "processed_data/library_master_vs_hunt_master_enriched_summary.json"
OUT_MD = ROOT / "processed_data/library_master_vs_hunt_master_enriched.md"

COMPARE_FIELD_MAP = {
    "database_hunt_name": "hunt_name",
    "database_weapon": "weapon",
    "database_hunt_type": "hunt_type",
    "database_permits_2026_res": "permits_2026_res",
    "database_permits_2026_nr": "permits_2026_nr",
    "database_permits_2026_total": "permits_2026_total",
    "database_permits_2026_source": "permits_2026_source",
    "database_permit_allotment_2026_res": "permit_allotment_2026_res",
    "database_permit_allotment_2026_nr": "permit_allotment_2026_nr",
    "database_permit_allotment_2026_total": "permit_allotment_2026_total",
    "database_permit_allotment_2026_source": "permit_allotment_2026_source",
    "database_permit_allotment_2026_source_file": "permit_allotment_2026_source_file",
    "database_permit_allotment_2026_status": "permit_allotment_2026_status",
}

OUT_FIELDS = [
    "record_id",
    "record_type",
    "library_title",
    "library_species",
    "library_area",
    "database_match_status",
    "database_hunt_code",
    "hunt_master_compare_status",
    "hunt_master_row_count",
    "hunt_master_residencies",
    "hunt_master_draw_pools",
    "hunt_master_point_row_count",
    "field_mismatch_count",
    "blank_database_runtime_value_count",
    "field_mismatches",
    "blank_database_runtime_values",
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])


def unique_values(rows: list[dict[str, str]], field: str) -> list[str]:
    return sorted({row.get(field, "").strip() for row in rows if row.get(field, "").strip()})


def compare_row(row: dict[str, str], hunt_rows: list[dict[str, str]]) -> dict[str, str]:
    record_type = row.get("record_type", "")
    code = row.get("database_hunt_code", "")
    db_match_status = row.get("database_match_status", "")
    if record_type == "document":
        status = "DOCUMENT_ROW_NOT_HUNT_CODED"
    elif not code:
        status = "NO_RECONCILED_HUNT_CODE"
    elif not hunt_rows:
        status = "MISSING_FROM_HUNT_MASTER_ENRICHED"
    else:
        status = "FOUND"

    field_mismatches: list[str] = []
    blank_database_runtime_values: list[str] = []
    if status == "FOUND":
        for library_field, runtime_field in COMPARE_FIELD_MAP.items():
            database_value = row.get(library_field, "").strip()
            runtime_values = unique_values(hunt_rows, runtime_field)
            if database_value:
                if database_value not in runtime_values:
                    joined = " | ".join(runtime_values[:8])
                    if len(runtime_values) > 8:
                        joined += " | ..."
                    field_mismatches.append(f"{library_field}->{runtime_field}: {database_value!r} not in [{joined}]")
            elif runtime_values:
                joined = " | ".join(runtime_values[:8])
                if len(runtime_values) > 8:
                    joined += " | ..."
                blank_database_runtime_values.append(f"{library_field}->{runtime_field}: database blank, runtime has [{joined}]")
        if field_mismatches:
            status = "FOUND_FIELD_MISMATCH"
        elif db_match_status not in {"MATCH_HIGH", ""}:
            status = "FOUND_PRIOR_REVIEW_REQUIRED"
        else:
            status = "FOUND_ALIGNED"

    return {
        "record_id": row.get("record_id", ""),
        "record_type": record_type,
        "library_title": row.get("title", ""),
        "library_species": row.get("species", ""),
        "library_area": row.get("area", ""),
        "database_match_status": db_match_status,
        "database_hunt_code": code,
        "hunt_master_compare_status": status,
        "hunt_master_row_count": str(len(hunt_rows)),
        "hunt_master_residencies": "|".join(unique_values(hunt_rows, "residency")),
        "hunt_master_draw_pools": "|".join(unique_values(hunt_rows, "draw_pool")),
        "hunt_master_point_row_count": str(len({(r.get("residency", ""), r.get("points", ""), r.get("draw_pool", "")) for r in hunt_rows})),
        "field_mismatch_count": str(len(field_mismatches)),
        "blank_database_runtime_value_count": str(len(blank_database_runtime_values)),
        "field_mismatches": "; ".join(field_mismatches),
        "blank_database_runtime_values": "; ".join(blank_database_runtime_values),
    }


def main() -> None:
    _, library_rows = read_csv(LIBRARY_RECONCILED)
    _, hunt_rows = read_csv(HUNT_MASTER)
    hunt_by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in hunt_rows:
        code = row.get("hunt_code", "").strip()
        if code:
            hunt_by_code[code].append(row)

    comparison_rows = [compare_row(row, hunt_by_code.get(row.get("database_hunt_code", ""), [])) for row in library_rows]
    write_csv(OUT_CSV, OUT_FIELDS, comparison_rows)

    status_counts = Counter(row["hunt_master_compare_status"] for row in comparison_rows)
    prior_status_counts = Counter(row.get("database_match_status", "") for row in library_rows)
    library_codes = {row.get("database_hunt_code", "") for row in library_rows if row.get("database_hunt_code", "")}
    hunt_codes = set(hunt_by_code)
    found_codes = library_codes & hunt_codes
    missing_codes = library_codes - hunt_codes
    mismatch_rows = [row for row in comparison_rows if row["hunt_master_compare_status"] == "FOUND_FIELD_MISMATCH"]
    mismatch_field_counts: Counter[str] = Counter()
    for row in mismatch_rows:
        for part in row["field_mismatches"].split("; "):
            if "->" in part and ":" in part:
                mismatch_field_counts[part.split(":", 1)[0]] += 1

    summary = {
        "artifact": "library_master_vs_hunt_master_enriched",
        "status": "REVIEW_REQUIRED" if mismatch_rows or missing_codes else "ALIGNED",
        "library_record_count": len(library_rows),
        "library_reconciled_hunt_code_count": len(library_codes),
        "hunt_master_row_count": len(hunt_rows),
        "hunt_master_unique_hunt_codes": len(hunt_codes),
        "library_codes_found_in_hunt_master": len(found_codes),
        "library_codes_missing_from_hunt_master": len(missing_codes),
        "missing_library_codes": sorted(missing_codes),
        "hunt_master_compare_status_counts": dict(sorted(status_counts.items())),
        "library_database_match_status_counts": dict(sorted(prior_status_counts.items())),
        "field_mismatch_row_count": len(mismatch_rows),
        "field_mismatch_counts": dict(sorted(mismatch_field_counts.items())),
        "field_mismatch_examples": mismatch_rows[:20],
        "notes": [
            "hunt_master_enriched repeats hunt codes by residency, point bucket, and draw pool.",
            "Document-only library rows are not expected to have hunt-code matches.",
            "Field comparisons check whether the database value appears anywhere in the runtime rows for the same hunt code.",
        ],
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Library Master vs Hunt Master Enriched",
        "",
        f"- Status: `{summary['status']}`",
        f"- Library rows: `{summary['library_record_count']}`",
        f"- Library reconciled hunt codes: `{summary['library_reconciled_hunt_code_count']}`",
        f"- Hunt master rows: `{summary['hunt_master_row_count']}`",
        f"- Hunt master unique hunt codes: `{summary['hunt_master_unique_hunt_codes']}`",
        f"- Library codes found in hunt master: `{summary['library_codes_found_in_hunt_master']}`",
        f"- Library codes missing from hunt master: `{summary['library_codes_missing_from_hunt_master']}`",
        f"- Field mismatch rows: `{summary['field_mismatch_row_count']}`",
        "",
        "## Compare Status Counts",
        "",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## Field Mismatch Counts", ""])
    for field, count in sorted(mismatch_field_counts.items()):
        lines.append(f"- `{field}`: `{count}`")
    lines.extend(["", "The detailed row-level comparison is in `processed_data/library_master_vs_hunt_master_enriched.csv`."])
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
