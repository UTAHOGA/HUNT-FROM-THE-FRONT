from __future__ import annotations

import csv
import gzip
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\tyler\Desktop\GitHub\HUNT-BUILDER")
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
AGE_MASTER = ROOT / "processed_data" / "harvest_age_features_by_hunt_code_latest.csv"
AUDIT_JSON = ROOT / "processed_data" / "audits" / "reviewed_age_boundary_promotion_2026_audit.json"
AUDIT_CSV = ROOT / "processed_data" / "audits" / "reviewed_age_boundary_promotion_2026_audit.csv"

TARGET_FILES = [
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv",
    ROOT / "processed_data" / "point_ladder_view.csv",
    ROOT / "processed_data" / "hunt_master_enriched.csv",
    ROOT / "processed_data" / "hunt_unit_reference_linked.csv",
    ROOT / "processed_data" / "draw_reality_engine_v2.csv",
    ROOT / "processed_data" / "draw_reality_engine.csv",
    ROOT / "processed_data" / "draw_reality_engine_predictive_v2.csv",
]

PROMOTED_COLUMNS = [
    "current_age_3yr_average",
    "average_harvest_age",
    "average_harvest_age_reported_hunt_year",
    "average_harvest_age_source_file",
    "average_harvest_age_review_status",
]


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm_code(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def display_number(value: Any) -> str:
    try:
        number = float(clean(value))
    except ValueError:
        return ""
    if number <= 0:
        return ""
    return f"{number:.1f}".rstrip("0").rstrip(".")


def is_gzip(path: Path) -> bool:
    return path.exists() and path.read_bytes()[:2] == b"\x1f\x8b"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]], bool]:
    gzipped = is_gzip(path)
    opener = gzip.open if gzipped else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), [dict(row) for row in reader], gzipped


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]], gzipped: bool) -> None:
    opener = gzip.open if gzipped else open
    with opener(path, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def insert_after(fieldnames: list[str], anchor: str, new_columns: list[str]) -> list[str]:
    fields = list(fieldnames)
    insert_at = fields.index(anchor) + 1 if anchor in fields else len(fields)
    for column in new_columns:
        if column in fields:
            continue
        fields.insert(insert_at, column)
        insert_at += 1
    return fields


def ensure_columns(fieldnames: list[str], path: Path) -> tuple[list[str], list[str]]:
    added: list[str] = []
    fields = list(fieldnames)

    if "boundary_id" not in fields:
        fields.append("boundary_id")
        added.append("boundary_id")

    if path == DATABASE:
        missing_promoted = [column for column in PROMOTED_COLUMNS if column not in fields]
        fields = insert_after(fields, "current_age_3yr_average", missing_promoted)
        added.extend(missing_promoted)
    else:
        for column in PROMOTED_COLUMNS:
            if column not in fields:
                fields.append(column)
                added.append(column)

    return fields, added


def load_pass_age() -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    _, rows, _ = read_csv(AGE_MASTER)
    for row in rows:
        if clean(row.get("review_status")).upper() != "PASS":
            continue
        code = norm_code(row.get("hunt_code"))
        age = display_number(row.get("average_harvest_age"))
        if not code or not age:
            continue
        try:
            year = int(float(clean(row.get("reported_hunt_year"))))
        except ValueError:
            year = 0
        prior_year = int(lookup.get(code, {}).get("average_harvest_age_reported_hunt_year", "0") or 0)
        if year >= prior_year:
            lookup[code] = {
                "average_harvest_age": age,
                "average_harvest_age_reported_hunt_year": str(year) if year else "",
                "average_harvest_age_source_file": clean(row.get("source_file")),
                "average_harvest_age_review_status": "PASS",
            }
    return lookup


def load_database_lookup(age_lookup: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    _, rows, _ = read_csv(DATABASE)
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        code = norm_code(row.get("hunt_code"))
        if not code:
            continue
        item = {
            "boundary_id": clean(row.get("boundary_id")),
            "current_age_3yr_average": display_number(row.get("current_age_3yr_average")),
        }
        item.update(age_lookup.get(code, {}))
        lookup[code] = item
    return lookup


def promote_file(path: Path, db_lookup: dict[str, dict[str, str]], age_lookup: dict[str, dict[str, str]]) -> dict[str, Any]:
    original_fields, rows, gzipped = read_csv(path)
    fields, added_columns = ensure_columns(original_fields, path)

    counts: Counter[str] = Counter()
    boundary_conflicts: list[dict[str, str]] = []
    rows_with_codes = 0

    for row in rows:
        code = norm_code(row.get("hunt_code"))
        if not code:
            counts["rows_without_hunt_code"] += 1
            continue
        rows_with_codes += 1
        source = db_lookup.get(code, {})
        age_source = age_lookup.get(code, {})

        if path == DATABASE:
            source = {
                "boundary_id": clean(row.get("boundary_id")),
                "current_age_3yr_average": display_number(row.get("current_age_3yr_average")),
                **age_source,
            }

        if source.get("boundary_id"):
            old_boundary = clean(row.get("boundary_id"))
            new_boundary = source["boundary_id"]
            if not old_boundary:
                counts["boundary_id_filled_blank"] += 1
            elif old_boundary != new_boundary:
                counts["boundary_id_overwritten_to_database"] += 1
                if len(boundary_conflicts) < 100:
                    boundary_conflicts.append(
                        {
                            "file": str(path.relative_to(ROOT)),
                            "hunt_code": code,
                            "old_boundary_id": old_boundary,
                            "database_boundary_id": new_boundary,
                        }
                    )
            row["boundary_id"] = new_boundary
        elif code not in db_lookup:
            counts["hunt_code_not_in_database"] += 1

        for column in PROMOTED_COLUMNS:
            if column == "current_age_3yr_average":
                value = source.get(column, "")
            else:
                value = age_source.get(column, "")

            old_value = clean(row.get(column))
            if value:
                if not old_value:
                    counts[f"{column}_filled_blank"] += 1
                elif old_value != value:
                    counts[f"{column}_overwritten"] += 1
                row[column] = value
            elif path == DATABASE and column != "current_age_3yr_average":
                if old_value:
                    counts[f"{column}_cleared_no_pass_source"] += 1
                row[column] = ""

    write_csv(path, fields, rows, gzipped)

    return {
        "file": str(path.relative_to(ROOT)),
        "rows": len(rows),
        "rows_with_hunt_code": rows_with_codes,
        "gzipped_csv_storage": gzipped,
        "columns_added": added_columns,
        "counts": dict(counts),
        "boundary_conflict_samples": boundary_conflicts,
    }


def main() -> None:
    age_lookup = load_pass_age()
    db_lookup_before = load_database_lookup(age_lookup)
    reports = []

    for path in TARGET_FILES:
        if not path.exists():
            reports.append({"file": str(path.relative_to(ROOT)), "missing": True})
            continue
        report = promote_file(path, db_lookup_before, age_lookup)
        reports.append(report)

    db_fields, db_rows, _ = read_csv(DATABASE)
    db_codes = {norm_code(row.get("hunt_code")) for row in db_rows if norm_code(row.get("hunt_code"))}
    age_codes_not_in_database = sorted(code for code in age_lookup if code not in db_codes)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "age_source": str(AGE_MASTER.relative_to(ROOT)),
        "database_source": str(DATABASE.relative_to(ROOT)),
        "pass_numeric_age_codes": len(age_lookup),
        "pass_numeric_age_codes_in_database": sum(1 for code in age_lookup if code in db_codes),
        "pass_numeric_age_codes_not_in_database": len(age_codes_not_in_database),
        "age_codes_not_in_database": age_codes_not_in_database,
        "target_files": reports,
        "outputs": {
            "audit_json": str(AUDIT_JSON.relative_to(ROOT)),
            "audit_csv": str(AUDIT_CSV.relative_to(ROOT)),
        },
    }

    AUDIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    with AUDIT_CSV.open("w", newline="", encoding="utf-8") as fh:
        fieldnames = [
            "file",
            "rows",
            "rows_with_hunt_code",
            "gzipped_csv_storage",
            "columns_added",
            "counts_json",
            "boundary_conflict_sample_count",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for report in reports:
            writer.writerow(
                {
                    "file": report.get("file", ""),
                    "rows": report.get("rows", ""),
                    "rows_with_hunt_code": report.get("rows_with_hunt_code", ""),
                    "gzipped_csv_storage": str(report.get("gzipped_csv_storage", "")),
                    "columns_added": "|".join(report.get("columns_added", [])),
                    "counts_json": json.dumps(report.get("counts", {}), sort_keys=True),
                    "boundary_conflict_sample_count": len(report.get("boundary_conflict_samples", [])),
                }
            )

    print(f"pass_numeric_age_codes={summary['pass_numeric_age_codes']}")
    print(f"pass_numeric_age_codes_in_database={summary['pass_numeric_age_codes_in_database']}")
    print(f"pass_numeric_age_codes_not_in_database={summary['pass_numeric_age_codes_not_in_database']}")
    for report in reports:
        print(f"{report.get('file')}: rows={report.get('rows')} added={report.get('columns_added')} counts={report.get('counts')}")
    print(f"audit_json={AUDIT_JSON}")
    print(f"audit_csv={AUDIT_CSV}")


if __name__ == "__main__":
    main()
