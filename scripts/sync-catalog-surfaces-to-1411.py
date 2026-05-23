"""Sync stale catalog surfaces to the current 1,411-code DATABASE universe."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_JSON = ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.json"
SOURCE_CSV = ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.csv"
CANONICAL_PLANNER = ROOT / "canonical" / "hunt-planner-2026.json"
ROOT_CANONICAL = ROOT / "hunt-master-canonical-2026.json"
GENERATED_PLANNER = ROOT / "generated" / "pages" / "hunt-planner.json"
PROCESSED_SOURCE_CSV = ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.csv"
DATABASE_CANDIDATE_CSV = ROOT / "data" / "hunt-master-canonical-2026-database-candidate.csv"
OUT_JSON = ROOT / "processed_data" / "catalog_surface_1411_sync_report.json"
OUT_MD = ROOT / "processed_data" / "catalog_surface_1411_sync_report.md"

APP_DEFAULTS = {
    "documents": [],
    "regulations_references": [],
    "tags_and_permits": [],
    "geometry": {
        "display_boundary_id": "",
        "dwr_boundary_id": "",
        "dwr_member_boundary_ids": [],
        "boundary_geojson_path": "",
        "boundary_kmz_path": "",
        "geometry_status": "unknown",
        "provenance": [
            {
                "source_file": "data/hunt-master-canonical-2026-source-of-truth.json",
                "method": "catalog_surface_1411_sync",
                "confidence": "medium",
                "notes": ["Added to close stale 1394/1305 catalog coverage gap."],
            }
        ],
    },
}

ACTIVE_SYNC_FIELDS = [
    "hunt_name",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "permit_allotment_2026_res",
    "permit_allotment_2026_nr",
    "permit_allotment_2026_total",
    "permit_allotment_2026_source",
    "permit_allotment_2026_source_file",
    "permit_allotment_2026_status",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def code_of(row: dict[str, Any]) -> str:
    return clean(row.get("hunt_code") or row.get("huntCode") or row.get("code")).upper()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_source_rows() -> list[dict[str, Any]]:
    data = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    return data.get("hunt_catalog", data) if isinstance(data, dict) else data


def rows_by_code(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {code_of(row): row for row in rows if code_of(row)}


def as_root_hunt_row(source_row: dict[str, Any]) -> dict[str, Any]:
    row = dict(source_row)
    code = code_of(row)
    hunt_name = clean(row.get("hunt_name") or row.get("title"))
    species = clean(row.get("species"))
    species_slug = species.lower().replace(" ", "-").replace("/", "-") or "unknown"
    row["huntCode"] = code
    row["code"] = code
    row["title"] = hunt_name
    row["unitName"] = hunt_name
    row["unitCode"] = clean(row.get("boundary_id") or row.get("unitCode"))
    row["boundaryId"] = clean(row.get("boundary_id") or row.get("boundaryId"))
    row["boundary_id_numeric"] = clean(row.get("boundary_id_numeric") or row.get("boundary_id"))
    row["boundary_token"] = clean(row.get("boundary_token") or row.get("boundary_id"))
    resolved = row.get("resolvedBoundaryIds")
    if not isinstance(resolved, list):
        row["resolvedBoundaryIds"] = [resolved] if clean(resolved) else []
    row["id"] = clean(row.get("id")) or f"hunt-{code.lower()}"
    row["species_id"] = clean(row.get("species_id")) or f"species-{species_slug}"
    row["season_id"] = clean(row.get("season_id")) or f"season-{code.lower()}"
    row["provenance"] = [
        {
            "source_file": "data/hunt-master-canonical-2026-source-of-truth.json",
            "method": "catalog_surface_1411_sync",
            "confidence": "high",
            "notes": ["Synced missing current DATABASE hunt code into root canonical catalog."],
        }
    ]
    for key, value in APP_DEFAULTS.items():
        row.setdefault(key, value)
    return row


def season_for(row: dict[str, Any]) -> dict[str, Any]:
    code = code_of(row)
    season = clean(row.get("season"))
    return {
        "id": clean(row.get("season_id")) or f"season-{code.lower()}",
        "hunt_code": code,
        "label": season,
        "raw_season_text": season,
        "start_date": {
            "value": None,
            "status": "needs_owner_input",
            "question": f"Parse start date for {code} from raw_season_text; confirm exact date before automation.",
        },
        "end_date": {
            "value": None,
            "status": "needs_owner_input",
            "question": f"Parse end date for {code} from raw_season_text; confirm exact date before automation.",
        },
        "date_status": "raw_text_only",
        "provenance": [
            {
                "source_file": "data/hunt-master-canonical-2026-source-of-truth.json",
                "method": "catalog_surface_1411_sync",
                "confidence": "high",
                "notes": [],
            }
        ],
    }


def sync_root_canonical(source_rows: list[dict[str, Any]]) -> dict[str, Any]:
    data = json.loads(ROOT_CANONICAL.read_text(encoding="utf-8"))
    source_by_code = rows_by_code(source_rows)
    existing_codes = {code_of(row) for row in data["hunt_catalog"]}
    changed_cells = 0
    for row in data["hunt_catalog"]:
        source = source_by_code.get(code_of(row))
        if not source:
            continue
        for field in ACTIVE_SYNC_FIELDS:
            if field in source and clean(row.get(field)) != clean(source.get(field)):
                row[field] = clean(source.get(field))
                changed_cells += 1
    missing_codes = sorted(set(source_by_code) - existing_codes)
    appended = [as_root_hunt_row(source_by_code[code]) for code in missing_codes]
    data["hunt_catalog"].extend(appended)
    existing_season_codes = {clean(row.get("hunt_code")).upper() for row in data.get("seasons", [])}
    data.setdefault("seasons", []).extend(season_for(row) for row in appended if code_of(row) not in existing_season_codes)
    ROOT_CANONICAL.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "file": ROOT_CANONICAL.relative_to(ROOT).as_posix(),
        "before_codes": len(existing_codes),
        "after_codes": len({code_of(row) for row in data["hunt_catalog"]}),
        "added_codes": missing_codes,
        "changed_cells": changed_cells,
        "seasons_count": len(data.get("seasons", [])),
    }


def sync_generated_planner() -> dict[str, Any]:
    source = json.loads(CANONICAL_PLANNER.read_text(encoding="utf-8"))
    generated = json.loads(GENERATED_PLANNER.read_text(encoding="utf-8"))
    before_rows = generated.get("hunt_catalog", [])
    before = len(before_rows)
    before_codes = set(rows_by_code(before_rows))
    source_codes = set(rows_by_code(source["hunt_catalog"]))
    generated["hunt_catalog"] = source["hunt_catalog"]
    GENERATED_PLANNER.write_text(json.dumps(generated, indent=2) + "\n", encoding="utf-8")
    return {
        "file": GENERATED_PLANNER.relative_to(ROOT).as_posix(),
        "before_codes": before,
        "after_codes": len(generated["hunt_catalog"]),
        "added_codes": sorted(source_codes - before_codes),
    }


def copy_processed_source_csv() -> dict[str, Any]:
    fields, rows = read_csv(SOURCE_CSV)
    _, old_rows = read_csv(PROCESSED_SOURCE_CSV)
    before = len({code_of(row) for row in old_rows})
    write_csv(PROCESSED_SOURCE_CSV, fields, rows)
    after = len({code_of(row) for row in rows})
    return {
        "file": PROCESSED_SOURCE_CSV.relative_to(ROOT).as_posix(),
        "before_codes": before,
        "after_codes": after,
        "added_count": after - before,
    }


def sync_candidate_csv(source_rows: list[dict[str, Any]]) -> dict[str, Any]:
    fields, candidate_rows = read_csv(DATABASE_CANDIDATE_CSV)
    source_by_code = rows_by_code(source_rows)
    changed_cells = 0
    for row in candidate_rows:
        source = source_by_code.get(code_of(row))
        if not source:
            continue
        for field in (
            "hunt_name",
            "permits_2026_res",
            "permits_2026_nr",
            "permits_2026_total",
            "permit_allotment_2026_res",
            "permit_allotment_2026_nr",
            "permit_allotment_2026_total",
        ):
            if field in row and field in source and clean(row.get(field)) != clean(source.get(field)):
                row[field] = clean(source.get(field))
                changed_cells += 1
    write_csv(DATABASE_CANDIDATE_CSV, fields, candidate_rows)
    return {
        "file": DATABASE_CANDIDATE_CSV.relative_to(ROOT).as_posix(),
        "codes": len({code_of(row) for row in candidate_rows}),
        "changed_cells": changed_cells,
    }


def write_report(results: list[dict[str, Any]]) -> None:
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": SOURCE_JSON.relative_to(ROOT).as_posix(),
        "target_hunt_code_count": 1411,
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Catalog Surface 1,411 Sync Report",
        "",
        f"Generated UTC: {summary['generated_at_utc']}",
        f"Target hunt-code count: {summary['target_hunt_code_count']}",
        "",
        "| File | Before | After | Notes |",
        "| --- | ---: | ---: | --- |",
    ]
    for result in results:
        notes = []
        if result.get("added_codes"):
            notes.append(f"added {len(result['added_codes'])} codes")
        if result.get("added_count"):
            notes.append(f"added {result['added_count']} codes")
        if result.get("changed_cells"):
            notes.append(f"changed {result['changed_cells']} cells")
        lines.append(
            f"| `{result['file']}` | {result.get('before_codes', result.get('codes', ''))} | {result.get('after_codes', result.get('codes', ''))} | {', '.join(notes) or 'synced'} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    source_rows = load_source_rows()
    results = [
        sync_root_canonical(source_rows),
        sync_generated_planner(),
        copy_processed_source_csv(),
        sync_candidate_csv(source_rows),
    ]
    write_report(results)
    print(json.dumps({"results": results, "report": OUT_JSON.relative_to(ROOT).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
