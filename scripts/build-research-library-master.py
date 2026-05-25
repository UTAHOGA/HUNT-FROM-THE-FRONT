#!/usr/bin/env python3
"""Build a governed research library master with explicit hunt-code mapping fields.

The existing library-master is useful as a catalog, but it cannot be promoted as
truth while hunt_code/boundary_id are absent. This builder follows the same
truth-output pattern as the draw/harvest database scripts: source catalog in,
normalized truth candidate out, validation summary beside it.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HUNTS_ROOT = Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS")

SOURCE_LIBRARY = ROOT / "pipeline/RAW/hunt_unit_database/library-master.csv"
RECONCILED_LIBRARY = ROOT / "pipeline/RAW/hunt_unit_database/library-master.reconciled.csv"
DATABASE = HUNTS_ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
LOCAL_DATABASE_FALLBACK = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
HUNT_MASTER = ROOT / "processed_data/hunt_master_enriched.csv"
CROSSWALK = ROOT / "data_truth/crosswalk_truth/normalized/current_to_historical_hunt_code_crosswalk_2026.csv"

TRUTH_DIR = ROOT / "data_truth/research_library_truth/normalized"
VALIDATION_DIR = ROOT / "data_truth/research_library_truth/validation"
PROCESSED_DIR = ROOT / "processed_data"

MASTER_CSV = TRUTH_DIR / "research_library_master.csv"
MASTER_JSON = TRUTH_DIR / "research_library_master.json"
SUMMARY_JSON = VALIDATION_DIR / "research_library_master_summary.json"
GAPS_CSV = VALIDATION_DIR / "research_library_master_mapping_gaps.csv"
PROCESSED_CSV = PROCESSED_DIR / "research_library_master.csv"
PROCESSED_MD = PROCESSED_DIR / "research_library_master.md"

OUTPUT_FIELDS = [
    "research_record_id",
    "source_record_id",
    "source_document_id",
    "record_type",
    "mapping_scope",
    "hunt_code",
    "boundary_id",
    "hunt_code_mapping_status",
    "boundary_id_mapping_status",
    "candidate_hunt_code",
    "candidate_boundary_id",
    "candidate_historical_hunt_code",
    "candidate_historical_relationship",
    "candidate_match_status",
    "candidate_hunt_name",
    "candidate_species",
    "candidate_sex_type",
    "candidate_weapon",
    "candidate_hunt_type",
    "candidate_season",
    "candidate_permits_2026_res",
    "candidate_permits_2026_nr",
    "candidate_permits_2026_total",
    "candidate_permits_2026_source",
    "source_title",
    "source_species",
    "source_category",
    "source_organization",
    "source_group",
    "source_area",
    "source_condition",
    "year_start",
    "year_end",
    "public_visible",
    "prediction_engine_source",
    "source_pdf",
    "source_page",
    "source_repo_path",
    "source_file_status",
    "source_sha256",
    "data_status",
    "source_truth_status",
    "mapping_review_required",
    "mapping_method",
    "mapping_notes",
    "original_notes",
]

REQUIRED_MAPPING_FIELDS = [
    "hunt_code",
    "boundary_id",
    "hunt_code_mapping_status",
    "boundary_id_mapping_status",
    "candidate_hunt_code",
    "candidate_boundary_id",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_bool(value: str) -> str:
    return "YES" if (value or "").strip().lower() in {"true", "yes", "1"} else "NO"


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def resolve_source_path(row: dict[str, str]) -> Path | None:
    candidates = [
        row.get("source_repo_path", ""),
        row.get("file_path", ""),
        row.get("source_pdf", ""),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.is_absolute():
            path = ROOT / candidate
        if path.exists() and path.is_file():
            return path
    return None


def sha256_for_path(path: Path | None) -> str:
    if path is None:
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_document_id(row: dict[str, str]) -> str:
    if row.get("record_type") == "document":
        return row.get("record_id", "")
    source_pdf = (row.get("source_pdf") or row.get("source_repo_path") or row.get("file_path") or "").lower()
    if "2022" in source_pdf and "2024" in source_pdf and "conservation" in source_pdf:
        return "doc_2022_2024_conservation_permits"
    if "conservation" in (row.get("title", "").lower()):
        return "doc_2022_2024_conservation_permits"
    return ""


def load_database() -> dict[str, dict[str, str]]:
    database_path = DATABASE if DATABASE.exists() else LOCAL_DATABASE_FALLBACK
    rows = read_csv(database_path)
    return {row["hunt_code"]: row for row in rows if row.get("hunt_code")}


def load_hunt_master_codes() -> set[str]:
    if not HUNT_MASTER.exists():
        return set()
    return {row["hunt_code"] for row in read_csv(HUNT_MASTER) if row.get("hunt_code")}


def load_crosswalk() -> dict[str, dict[str, str]]:
    if not CROSSWALK.exists():
        return {}
    return {row["current_hunt_code"]: row for row in read_csv(CROSSWALK) if row.get("current_hunt_code")}


def mapping_for_row(
    row: dict[str, str],
    database: dict[str, dict[str, str]],
    crosswalk: dict[str, dict[str, str]],
) -> dict[str, str]:
    record_type = row.get("record_type", "")
    candidate_code = row.get("database_hunt_code", "")
    database_row = database.get(candidate_code, {}) if candidate_code else {}
    crosswalk_row = crosswalk.get(candidate_code, {}) if candidate_code else {}

    if record_type == "document":
        return {
            "mapping_scope": "DOCUMENT_LEVEL",
            "hunt_code": "",
            "boundary_id": "",
            "hunt_code_mapping_status": "DOCUMENT_LEVEL_MAPPING_REQUIRED",
            "boundary_id_mapping_status": "DOCUMENT_LEVEL_MAPPING_REQUIRED",
            "mapping_review_required": "YES",
            "mapping_method": "document_catalog_row_not_extracted_to_hunt_code_rows",
            "mapping_notes": "Document rows must be extracted into per-hunt-code rows before promotion.",
        }

    if candidate_code:
        return {
            "mapping_scope": "PERMIT_ALLOCATION_ROW",
            "hunt_code": "",
            "boundary_id": "",
            "hunt_code_mapping_status": "HISTORICAL_PREFIX_REVIEW_REQUIRED",
            "boundary_id_mapping_status": "HISTORICAL_PREFIX_REVIEW_REQUIRED",
            "mapping_review_required": "YES",
            "mapping_method": "candidate_from_library_database_reconciliation_not_promoted",
            "mapping_notes": (
                "Candidate only. The 2022-2024 conservation rows predate/current-prefix changes; "
                "current hunt_code and boundary_id require reviewed crosswalk promotion."
            ),
            "candidate_boundary_id": database_row.get("boundary_id", ""),
            "candidate_historical_hunt_code": crosswalk_row.get("historical_hunt_code", ""),
            "candidate_historical_relationship": crosswalk_row.get("relationship_type", ""),
        }

    return {
        "mapping_scope": "UNKNOWN_OR_UNMAPPED_ROW",
        "hunt_code": "",
        "boundary_id": "",
        "hunt_code_mapping_status": "UNMAPPED_REVIEW_REQUIRED",
        "boundary_id_mapping_status": "UNMAPPED_REVIEW_REQUIRED",
        "mapping_review_required": "YES",
        "mapping_method": "no_candidate_hunt_code_available",
        "mapping_notes": "No candidate hunt code is available; source row must be reviewed manually.",
    }


def build_rows() -> tuple[list[dict[str, str]], dict]:
    source_rows = read_csv(SOURCE_LIBRARY)
    reconciled_rows = {row["record_id"]: row for row in read_csv(RECONCILED_LIBRARY)}
    database = load_database()
    hunt_master_codes = load_hunt_master_codes()
    crosswalk = load_crosswalk()

    output_rows: list[dict[str, str]] = []
    for index, source_row in enumerate(source_rows, start=1):
        row = {**source_row, **reconciled_rows.get(source_row.get("record_id", ""), {})}
        candidate_code = row.get("database_hunt_code", "")
        database_row = database.get(candidate_code, {}) if candidate_code else {}
        path = resolve_source_path(row)
        mapping = mapping_for_row(row, database, crosswalk)

        output_rows.append(
            {
                "research_record_id": f"research_library_{index:04d}",
                "source_record_id": row.get("record_id", ""),
                "source_document_id": source_document_id(row),
                "record_type": row.get("record_type", ""),
                "mapping_scope": mapping.get("mapping_scope", ""),
                "hunt_code": mapping.get("hunt_code", ""),
                "boundary_id": mapping.get("boundary_id", ""),
                "hunt_code_mapping_status": mapping.get("hunt_code_mapping_status", ""),
                "boundary_id_mapping_status": mapping.get("boundary_id_mapping_status", ""),
                "candidate_hunt_code": candidate_code,
                "candidate_boundary_id": mapping.get("candidate_boundary_id", ""),
                "candidate_historical_hunt_code": mapping.get("candidate_historical_hunt_code", ""),
                "candidate_historical_relationship": mapping.get("candidate_historical_relationship", ""),
                "candidate_match_status": row.get("database_match_status", ""),
                "candidate_hunt_name": database_row.get("hunt_name", row.get("database_hunt_name", "")),
                "candidate_species": database_row.get("species", row.get("database_species", "")),
                "candidate_sex_type": database_row.get("sex_type", row.get("database_sex_type", "")),
                "candidate_weapon": database_row.get("weapon", row.get("database_weapon", "")),
                "candidate_hunt_type": database_row.get("hunt_type", row.get("database_hunt_type", "")),
                "candidate_season": database_row.get("season", row.get("database_season", "")),
                "candidate_permits_2026_res": database_row.get(
                    "permits_2026_res", row.get("database_permits_2026_res", "")
                ),
                "candidate_permits_2026_nr": database_row.get(
                    "permits_2026_nr", row.get("database_permits_2026_nr", "")
                ),
                "candidate_permits_2026_total": database_row.get(
                    "permits_2026_total", row.get("database_permits_2026_total", "")
                ),
                "candidate_permits_2026_source": database_row.get(
                    "permits_2026_source", row.get("database_permits_2026_source", "")
                ),
                "source_title": row.get("title", ""),
                "source_species": row.get("species", ""),
                "source_category": row.get("category", ""),
                "source_organization": row.get("organization", ""),
                "source_group": row.get("group", ""),
                "source_area": row.get("area", ""),
                "source_condition": row.get("condition", ""),
                "year_start": row.get("year_start", ""),
                "year_end": row.get("year_end", ""),
                "public_visible": normalize_bool(row.get("public_visible", "")),
                "prediction_engine_source": normalize_bool(row.get("prediction_engine_source", "")),
                "source_pdf": row.get("source_pdf", ""),
                "source_page": row.get("source_page", ""),
                "source_repo_path": row.get("source_repo_path") or row.get("file_path", ""),
                "source_file_status": "FOUND" if path else row.get("document_file_status", "NOT_RESOLVED"),
                "source_sha256": sha256_for_path(path),
                "data_status": row.get("data_status", ""),
                "source_truth_status": "CATALOG_ONLY_NOT_TRUTH",
                "mapping_review_required": mapping.get("mapping_review_required", "YES"),
                "mapping_method": mapping.get("mapping_method", ""),
                "mapping_notes": mapping.get("mapping_notes", ""),
                "original_notes": row.get("notes", ""),
            }
        )

    candidate_codes = {row["candidate_hunt_code"] for row in output_rows if row.get("candidate_hunt_code")}
    summary = {
        "artifact": "research_library_master",
        "status": "REVIEW_REQUIRED",
        "source_library": relative(SOURCE_LIBRARY),
        "source_reconciled_library": relative(RECONCILED_LIBRARY),
        "database_source": relative(DATABASE if DATABASE.exists() else LOCAL_DATABASE_FALLBACK),
        "record_count": len(output_rows),
        "source_record_count": len(source_rows),
        "record_type_counts": dict(sorted(Counter(row["record_type"] for row in output_rows).items())),
        "mapping_scope_counts": dict(sorted(Counter(row["mapping_scope"] for row in output_rows).items())),
        "hunt_code_mapping_status_counts": dict(
            sorted(Counter(row["hunt_code_mapping_status"] for row in output_rows).items())
        ),
        "boundary_id_mapping_status_counts": dict(
            sorted(Counter(row["boundary_id_mapping_status"] for row in output_rows).items())
        ),
        "review_required_rows": sum(1 for row in output_rows if row["mapping_review_required"] == "YES"),
        "reviewed_hunt_code_rows": sum(1 for row in output_rows if row.get("hunt_code")),
        "reviewed_boundary_id_rows": sum(1 for row in output_rows if row.get("boundary_id")),
        "candidate_hunt_code_rows": sum(1 for row in output_rows if row.get("candidate_hunt_code")),
        "candidate_hunt_code_unique_count": len(candidate_codes),
        "candidate_boundary_id_rows": sum(1 for row in output_rows if row.get("candidate_boundary_id")),
        "candidate_historical_hunt_code_rows": sum(
            1 for row in output_rows if row.get("candidate_historical_hunt_code")
        ),
        "candidate_codes_missing_database": sorted(code for code in candidate_codes if code not in database),
        "candidate_codes_missing_hunt_master": sorted(code for code in candidate_codes if code not in hunt_master_codes),
        "missing_required_mapping_fields": [
            field for field in REQUIRED_MAPPING_FIELDS if field not in OUTPUT_FIELDS
        ],
        "duplicate_research_record_ids": [
            record_id
            for record_id, count in Counter(row["research_record_id"] for row in output_rows).items()
            if count > 1
        ],
        "law": [
            "Every research library row must carry hunt_code and boundary_id columns.",
            "Blank reviewed hunt_code/boundary_id fields require explicit mapping status fields.",
            "Candidate hunt codes and candidate boundary IDs are not truth fields.",
            "Historical/current prefix changes must flow through the crosswalk before promotion.",
            "Document-level rows must be extracted into per-hunt-code rows before they can feed prediction/runtime data.",
        ],
        "outputs": {
            "master_csv": relative(MASTER_CSV),
            "master_json": relative(MASTER_JSON),
            "summary_json": relative(SUMMARY_JSON),
            "mapping_gaps_csv": relative(GAPS_CSV),
            "processed_csv": relative(PROCESSED_CSV),
            "processed_md": relative(PROCESSED_MD),
        },
    }

    blockers = []
    if summary["record_count"] != summary["source_record_count"]:
        blockers.append("SOURCE_ROW_COUNT_MISMATCH")
    if summary["missing_required_mapping_fields"]:
        blockers.append("MISSING_REQUIRED_MAPPING_FIELDS")
    if summary["duplicate_research_record_ids"]:
        blockers.append("DUPLICATE_RESEARCH_RECORD_IDS")
    if summary["candidate_codes_missing_database"]:
        blockers.append("CANDIDATE_CODES_MISSING_DATABASE")
    if summary["candidate_codes_missing_hunt_master"]:
        blockers.append("CANDIDATE_CODES_MISSING_HUNT_MASTER")
    summary["blockers"] = blockers
    summary["blocker_count"] = len(blockers)
    if blockers:
        summary["status"] = "BLOCKED"

    return output_rows, summary


def write_markdown(summary: dict) -> None:
    lines = [
        "# Research Library Master",
        "",
        "This is the governed research-library master generated from the existing library catalog.",
        "",
        "## Status",
        "",
        f"- Status: `{summary['status']}`",
        f"- Rows: `{summary['record_count']}`",
        f"- Reviewed hunt-code rows: `{summary['reviewed_hunt_code_rows']}`",
        f"- Candidate hunt-code rows: `{summary['candidate_hunt_code_rows']}`",
        f"- Unique candidate hunt codes: `{summary['candidate_hunt_code_unique_count']}`",
        f"- Rows requiring review: `{summary['review_required_rows']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        "",
        "## Law",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["law"])
    lines.extend(
        [
            "",
            "## Mapping Status Counts",
            "",
        ]
    )
    for key, value in summary["hunt_code_mapping_status_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Outputs", ""])
    for label, path in summary["outputs"].items():
        lines.append(f"- `{label}`: `{path}`")
    PROCESSED_MD.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows, summary = build_rows()
    gaps = [row for row in rows if row.get("mapping_review_required") == "YES"]

    write_csv(MASTER_CSV, rows, OUTPUT_FIELDS)
    write_json(MASTER_JSON, {"metadata": summary, "rows": rows})
    write_json(SUMMARY_JSON, summary)
    write_csv(GAPS_CSV, gaps, OUTPUT_FIELDS)
    write_csv(PROCESSED_CSV, rows, OUTPUT_FIELDS)
    write_markdown(summary)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["blocker_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
