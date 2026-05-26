#!/usr/bin/env python3
"""Fill blank 2026 DATABASE boundary IDs from reviewed JSON/GeoJSON sources.

The script only promotes exact evidence:
- direct HUNT_NUMBER -> BOUNDARYID matches from official hunt-table JSON files;
- exact hunt-name matches from official species hunt-table JSON files;
- exact unique hunt-name matches from the Utah DWR boundary GeoJSON layer.

No fuzzy boundary IDs are promoted.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
ELK_ANTLERLESS_OFFICIAL_PATH = ROOT / "data/elk_antlerless_hunt_table_official.json"
PRONGHORN_OFFICIAL_PATH = ROOT / "data/pronghorn_hunt_table_official.json"
BOUNDARY_GEOJSON_PATH = ROOT / "data/hunt_boundaries.geojson"

AUDIT_PATH = ROOT / "data_truth/crosswalk_truth/validation/database_boundary_id_fill_2026_audit.csv"
SUMMARY_PATH = ROOT / "data_truth/crosswalk_truth/validation/database_boundary_id_fill_2026_summary.json"
MARKDOWN_PATH = ROOT / "processed_data/database_boundary_id_fill_2026.md"

AUDIT_COLUMNS = [
    "hunt_code",
    "hunt_name",
    "species",
    "previous_boundary_id",
    "promoted_boundary_id",
    "candidate_boundary_id",
    "boundary_id_mapping_status",
    "match_method",
    "source_file",
    "source_sha256",
    "source_boundary_name",
    "source_hunt_code",
    "review_note",
]

REVIEW_TARGET_CODES: set[str] = set()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader], reader.fieldnames or []


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def write_database(rows: list[dict[str, str]], columns: list[str]) -> None:
    with DATABASE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def official_feature_records(path: Path) -> list[dict[str, str]]:
    data = load_json(path)
    features = data.get("features", []) if isinstance(data, dict) else data
    records: list[dict[str, str]] = []
    for feature in features:
        attrs = feature.get("attributes", {})
        code = str(attrs.get("HUNT_NUMBER") or "").strip()
        boundary_id = str(attrs.get("BOUNDARYID") or "").strip()
        boundary_name = str(attrs.get("BOUNDARY_NAME") or "").strip()
        if code and boundary_id and boundary_name:
            records.append(
                {
                    "hunt_code": code,
                    "boundary_id": boundary_id,
                    "boundary_name": boundary_name,
                    "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "source_sha256": sha256(path),
                }
            )
    return records


def boundary_geojson_records(path: Path) -> list[dict[str, str]]:
    data = load_json(path)
    records: list[dict[str, str]] = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        boundary_id = str(
            props.get("BOUNDARYID")
            or props.get("BoundaryID")
            or props.get("boundary_id")
            or ""
        ).strip()
        boundary_name = str(
            props.get("BOUNDARY_NAME")
            or props.get("Boundary_Name")
            or props.get("boundary_name")
            or ""
        ).strip()
        if boundary_id and boundary_name:
            records.append(
                {
                    "hunt_code": "",
                    "boundary_id": boundary_id,
                    "boundary_name": boundary_name,
                    "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "source_sha256": sha256(path),
                }
            )
    return records


def build_indexes() -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    official_records = official_feature_records(ELK_ANTLERLESS_OFFICIAL_PATH) + official_feature_records(
        PRONGHORN_OFFICIAL_PATH
    )
    boundary_records = boundary_geojson_records(BOUNDARY_GEOJSON_PATH)

    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    official_by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    boundary_by_name: dict[str, list[dict[str, str]]] = defaultdict(list)

    for record in official_records:
        by_code[record["hunt_code"]].append(record)
        official_by_name[normalize_name(record["boundary_name"])].append(record)
    for record in boundary_records:
        boundary_by_name[normalize_name(record["boundary_name"])].append(record)

    return by_code, official_by_name, boundary_by_name


def unique_boundary(records: list[dict[str, str]]) -> dict[str, str] | None:
    ids = {record["boundary_id"] for record in records if record.get("boundary_id")}
    if len(ids) != 1:
        return None
    # Prefer the first record carrying the unique ID. Multiple hunt numbers can
    # share the same boundary; that is still exact boundary evidence.
    return next(record for record in records if record.get("boundary_id") in ids)


def choose_boundary(
    row: dict[str, str],
    by_code: dict[str, list[dict[str, str]]],
    official_by_name: dict[str, list[dict[str, str]]],
    boundary_by_name: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, str] | None, str, str]:
    code = row["hunt_code"]
    name_key = normalize_name(row["hunt_name"])

    direct_candidates = [
        record for record in by_code.get(code, []) if normalize_name(record["boundary_name"]) == name_key
    ]
    direct = unique_boundary(direct_candidates)
    if direct:
        return direct, "DIRECT_OFFICIAL_HUNT_CODE_JSON", "Exact HUNT_NUMBER match in official DWR hunt-table JSON."

    official_name = unique_boundary(official_by_name.get(name_key, []))
    if official_name:
        return official_name, "EXACT_OFFICIAL_BOUNDARY_NAME_JSON", "Exact boundary-name match in official DWR hunt-table JSON."

    boundary_name = unique_boundary(boundary_by_name.get(name_key, []))
    if boundary_name:
        return boundary_name, "EXACT_UNIQUE_DWR_BOUNDARY_GEOJSON_NAME", "Exact unique boundary-name match in DWR boundary GeoJSON."

    return None, "UNRESOLVED", "No exact unique boundary ID evidence found."


def build_and_apply() -> tuple[list[dict[str, str]], dict[str, object]]:
    database_rows, columns = read_csv(DATABASE_PATH)
    by_code, official_by_name, boundary_by_name = build_indexes()
    blank_rows = [row for row in database_rows if not row.get("boundary_id")]
    target_rows = [
        row for row in database_rows if not row.get("boundary_id") or row.get("hunt_code") in REVIEW_TARGET_CODES
    ]
    audit_rows: list[dict[str, str]] = []

    for row in target_rows:
        match, method, note = choose_boundary(row, by_code, official_by_name, boundary_by_name)
        if match:
            previous_boundary_id = row.get("boundary_id", "")
            row["boundary_id"] = match["boundary_id"]
            if previous_boundary_id and previous_boundary_id != match["boundary_id"]:
                status = "REVIEWED_BOUNDARY_ID_CORRECTED"
            elif previous_boundary_id:
                status = "REVIEWED_BOUNDARY_ID_CONFIRMED"
            else:
                status = "REVIEWED_BOUNDARY_ID_PROMOTED"
            audit_rows.append(
                {
                    "hunt_code": row["hunt_code"],
                    "hunt_name": row["hunt_name"],
                    "species": row["species"],
                    "previous_boundary_id": previous_boundary_id,
                    "promoted_boundary_id": match["boundary_id"],
                    "candidate_boundary_id": match["boundary_id"],
                    "boundary_id_mapping_status": status,
                    "match_method": method,
                    "source_file": match["source_file"],
                    "source_sha256": match["source_sha256"],
                    "source_boundary_name": match["boundary_name"],
                    "source_hunt_code": match.get("hunt_code", ""),
                    "review_note": (
                        f"{note} Corrected prior DATABASE boundary_id {previous_boundary_id} after stricter source-name validation."
                        if previous_boundary_id and previous_boundary_id != match["boundary_id"]
                        else note
                    ),
                }
            )
        else:
            audit_rows.append(
                {
                    "hunt_code": row["hunt_code"],
                    "hunt_name": row["hunt_name"],
                    "species": row["species"],
                    "previous_boundary_id": "",
                    "promoted_boundary_id": "",
                    "candidate_boundary_id": "",
                    "boundary_id_mapping_status": "UNRESOLVED_BOUNDARY_ID",
                    "match_method": method,
                    "source_file": "",
                    "source_sha256": "",
                    "source_boundary_name": "",
                    "source_hunt_code": "",
                    "review_note": note,
                }
            )

    remaining_blank = [row["hunt_code"] for row in database_rows if not row.get("boundary_id")]
    counts: dict[str, int] = defaultdict(int)
    for row in database_rows:
        counts[row["hunt_code"]] += 1
    duplicate_codes = [code for code, count in counts.items() if code and count > 1]

    write_database(database_rows, columns)
    write_csv(AUDIT_PATH, audit_rows, AUDIT_COLUMNS)

    summary = {
        "artifact": "database_boundary_id_fill_2026",
        "database_source": str(DATABASE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "review_target_count": len(REVIEW_TARGET_CODES),
        "blank_boundary_id_before": len(blank_rows),
        "reviewed_count": sum(1 for row in audit_rows if row["boundary_id_mapping_status"].startswith("REVIEWED_")),
        "promoted_count": sum(1 for row in audit_rows if row["boundary_id_mapping_status"] == "REVIEWED_BOUNDARY_ID_PROMOTED"),
        "confirmed_count": sum(1 for row in audit_rows if row["boundary_id_mapping_status"] == "REVIEWED_BOUNDARY_ID_CONFIRMED"),
        "corrected_count": sum(1 for row in audit_rows if row["boundary_id_mapping_status"] == "REVIEWED_BOUNDARY_ID_CORRECTED"),
        "unresolved_count": sum(1 for row in audit_rows if row["boundary_id_mapping_status"] == "UNRESOLVED_BOUNDARY_ID"),
        "blank_boundary_id_after": len(remaining_blank),
        "remaining_blank_hunt_codes": remaining_blank,
        "duplicate_hunt_code_count": len(duplicate_codes),
        "duplicate_hunt_codes": duplicate_codes,
        "match_method_counts": dict(
            sorted(
                {
                    method: sum(1 for row in audit_rows if row["match_method"] == method)
                    for method in {row["match_method"] for row in audit_rows}
                }.items()
            )
        ),
        "blocker_count": len(remaining_blank) + len(duplicate_codes),
        "blockers": (
            (["BLANK_BOUNDARY_IDS_REMAIN"] if remaining_blank else [])
            + (["DUPLICATE_HUNT_CODES"] if duplicate_codes else [])
        ),
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit_rows, summary


def write_markdown(audit_rows: list[dict[str, str]], summary: dict[str, object]) -> None:
    MARKDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 2026 DATABASE Boundary ID Fill",
        "",
        "Blank boundary IDs were filled only from exact JSON/GeoJSON evidence.",
        "",
        f"- Blank before: {summary['blank_boundary_id_before']}",
        f"- Promoted: {summary['promoted_count']}",
        f"- Blank after: {summary['blank_boundary_id_after']}",
        f"- Blockers: {summary['blocker_count']}",
        "",
        "## Promoted Rows",
        "",
    ]
    for row in audit_rows:
        lines.append(
            f"- {row['hunt_code']}: {row['promoted_boundary_id'] or '(unresolved)'}; {row['match_method']}; {row['source_boundary_name']}"
        )
    MARKDOWN_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    audit_rows, summary = build_and_apply()
    write_markdown(audit_rows, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["blocker_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
