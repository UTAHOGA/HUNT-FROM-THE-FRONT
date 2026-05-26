"""Normalize and validate 2026 Rocky Mountain bighorn sheep permit numbers."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 rocky mountain bighorn user verified.csv"
RAC_RAM_SOURCE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_rac_oial_rocky_mountain_bighorn_sheep_permits.csv"
RAC_EWE_SOURCE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_rac_ewe_rocky_mountain_bighorn_sheep_permits.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"

REVIEWED_EXPORT = (
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 rocky mountain bighorn reviewed res-nr-total.csv"
)
NORMALIZED_OUT = ROOT / "data_truth/permit_overlay_truth/normalized/rocky_bighorn_permits_2026_canonical.csv"
DB_COMPARE_OUT = ROOT / "data_truth/permit_overlay_truth/validation/rocky_bighorn_permits_2026_vs_DATABASE.csv"
RAC_COMPARE_OUT = ROOT / "data_truth/permit_overlay_truth/validation/rocky_bighorn_permits_2026_vs_RAC.csv"
PARALLEL_OUT = (
    ROOT / "data_truth/permit_overlay_truth/validation/rocky_bighorn_public_vs_conservation_parallel_2026.csv"
)
SUMMARY_OUT = ROOT / "data_truth/permit_overlay_truth/validation/rocky_bighorn_permits_2026_summary.json"
REPORT_OUT = ROOT / "processed_data/rocky_bighorn_permits_2026_summary.md"

SOURCE_FILE_LABEL = "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 rocky mountain bighorn user verified.csv"

INPUT_FIELDS = [
    "hunt_name",
    "hunt_code",
    "sex_type",
    "species",
    "weapon",
    "hunt_type",
    "season",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "NOTES",
]

OUTPUT_FIELDS = [
    "hunt_name",
    "hunt_code",
    "boundary_id",
    "hunt_code_mapping_status",
    "boundary_id_mapping_status",
    "candidate_hunt_code",
    "candidate_boundary_id",
    "sex_type",
    "database_sex_type",
    "species",
    "weapon",
    "hunt_type",
    "season",
    "database_season",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "permit_count_status",
    "source_file",
    "source_sha256",
    "notes",
]

REVIEWED_FIELDS = [
    "hunt_name",
    "hunt_code",
    "boundary_id",
    "hunt_code_mapping_status",
    "boundary_id_mapping_status",
    "candidate_hunt_code",
    "candidate_boundary_id",
    "sex_type",
    "species",
    "weapon",
    "hunt_type",
    "season",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
]

DB_COMPARE_FIELDS = [
    "hunt_code",
    "source_hunt_name",
    "database_hunt_name",
    "source_res",
    "source_nr",
    "source_total",
    "database_res",
    "database_nr",
    "database_total",
    "database_boundary_id",
    "database_source",
    "numeric_comparison_status",
    "semantic_review_flags",
    "review_action",
]

RAC_COMPARE_FIELDS = [
    "hunt_code",
    "source_hunt_name",
    "rac_hunt_name",
    "source_res",
    "source_nr",
    "source_total",
    "rac_res",
    "rac_nr",
    "rac_total",
    "comparison_status",
]

PARALLEL_FIELDS = [
    "conservation_hunt_code",
    "conservation_hunt_name",
    "conservation_total",
    "public_parallel_hunt_codes",
    "public_parallel_hunt_names",
    "public_parallel_total",
    "relationship_type",
    "resolution_status",
    "notes",
]

CONSERVATION_PUBLIC_PARALLELS = {
    "RS1000": ["RS6700"],
    "RS1001": ["RS6701"],
    "RS1003": ["RS6703", "RS6704", "RS6722"],
    "RS1006": ["RS6712"],
}


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader], [
            (field or "").strip() for field in (reader.fieldnames or [])
        ]


def write_csv(path: Path, rows: Iterable[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_count(value: str) -> str:
    text = (value or "").strip()
    if text == "":
        return ""
    match = re.search(r":\s*(\d+)\b", text)
    if match:
        return match.group(1)
    return str(int(float(text.replace(",", ""))))


def as_int_text(value: object) -> str:
    text = str(value or "").strip()
    if text == "":
        return ""
    return str(int(float(text.replace(",", ""))))


def load_database() -> dict[str, dict[str, str]]:
    rows, _ = read_csv(DATABASE)
    return {row.get("hunt_code", ""): row for row in rows if row.get("hunt_code", "")}


def fill_count(source_value: str, database_value: str) -> tuple[str, str]:
    source_count = parse_count(source_value)
    if source_count != "":
        return source_count, "SOURCE_SPLIT"
    database_count = as_int_text(database_value)
    if database_count != "":
        return database_count, "DATABASE_CANONICAL_FILL"
    return "", "BLANK"


def permit_count_status(row: dict[str, str]) -> str:
    if row["permits_2026_res"] != "" and row["permits_2026_nr"] != "":
        return "FULL_SPLIT"
    if row["permits_2026_total"] != "":
        return "TOTAL_ONLY"
    return "NO_PUBLISHED_NUMERIC_PERMIT"


def normalize_source(database_by_code: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows, fields = read_csv(SOURCE)
    if fields != INPUT_FIELDS:
        raise ValueError(f"Unexpected Rocky Mountain bighorn source headers: {fields}")

    source_hash = sha256(SOURCE)
    normalized: list[dict[str, str]] = []
    for row in rows:
        code = row["hunt_code"]
        db_row = database_by_code.get(code, {})
        res, res_source = fill_count(row["permits_2026_res"], db_row.get("permits_2026_res", ""))
        nr, nr_source = fill_count(row["permits_2026_nr"], db_row.get("permits_2026_nr", ""))
        total, total_source = fill_count(row["permits_2026_total"], db_row.get("permits_2026_total", ""))
        if total and res != "" and nr != "" and int(total) != int(res) + int(nr):
            raise ValueError(f"Res/NonRes total mismatch for {code}: {res}+{nr}!={total}")
        source_notes = [row.get("NOTES", "")]
        if "DATABASE_CANONICAL_FILL" in {res_source, nr_source, total_source}:
            source_notes.append("Permit split populated from canonical DATABASE.csv because source row did not carry a count.")
        normalized.append(
            {
                "hunt_name": row["hunt_name"],
                "hunt_code": code,
                "boundary_id": db_row.get("boundary_id", ""),
                "hunt_code_mapping_status": "REVIEWED_CURRENT_HUNT_CODE",
                "boundary_id_mapping_status": "DATABASE_BOUNDARY_ID" if db_row.get("boundary_id") else "BOUNDARY_ID_MISSING",
                "candidate_hunt_code": code,
                "candidate_boundary_id": db_row.get("boundary_id", ""),
                "sex_type": row["sex_type"],
                "database_sex_type": db_row.get("sex_type", ""),
                "species": row["species"],
                "weapon": row["weapon"],
                "hunt_type": row["hunt_type"],
                "season": row["season"],
                "database_season": db_row.get("season", ""),
                "permits_2026_res": res,
                "permits_2026_nr": nr,
                "permits_2026_total": total,
                "permit_count_status": "FULL_SPLIT" if res and nr else ("TOTAL_ONLY" if total else "NO_PUBLISHED_NUMERIC_PERMIT"),
                "source_file": SOURCE_FILE_LABEL,
                "source_sha256": source_hash,
                "notes": " ".join(note for note in source_notes if note),
            }
        )

    codes = [row["hunt_code"] for row in normalized]
    duplicates = sorted(code for code, count in Counter(codes).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate Rocky Mountain bighorn hunt codes: {duplicates}")
    return normalized


def compare_database(normalized: list[dict[str, str]], database_by_code: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    comparison: list[dict[str, str]] = []
    for row in normalized:
        code = row["hunt_code"]
        db = database_by_code.get(code)
        if db is None:
            comparison.append(
                {
                    "hunt_code": code,
                    "source_hunt_name": row["hunt_name"],
                    "database_hunt_name": "",
                    "source_res": row["permits_2026_res"],
                    "source_nr": row["permits_2026_nr"],
                    "source_total": row["permits_2026_total"],
                    "database_res": "",
                    "database_nr": "",
                    "database_total": "",
                    "database_boundary_id": "",
                    "database_source": "",
                    "numeric_comparison_status": "MISSING_DATABASE_ROW",
                    "semantic_review_flags": "",
                    "review_action": "REVIEW_ADD_CURRENT_ROCKY_BIGHORN_ROW",
                }
            )
            continue
        db_res = as_int_text(db.get("permits_2026_res"))
        db_nr = as_int_text(db.get("permits_2026_nr"))
        db_total = as_int_text(db.get("permits_2026_total"))
        source_tuple = (row["permits_2026_res"], row["permits_2026_nr"], row["permits_2026_total"])
        db_tuple = (db_res, db_nr, db_total)
        numeric_status = "MATCH" if source_tuple == db_tuple else "PROTECTED_DATABASE_DIFFERENCE"
        semantic_flags = []
        if row["sex_type"] != db.get("sex_type", ""):
            semantic_flags.append("SEX_TYPE_REVIEW")
        if row["season"] != db.get("season", ""):
            semantic_flags.append("SEASON_TEXT_REVIEW")
        comparison.append(
            {
                "hunt_code": code,
                "source_hunt_name": row["hunt_name"],
                "database_hunt_name": db.get("hunt_name", ""),
                "source_res": row["permits_2026_res"],
                "source_nr": row["permits_2026_nr"],
                "source_total": row["permits_2026_total"],
                "database_res": db_res,
                "database_nr": db_nr,
                "database_total": db_total,
                "database_boundary_id": db.get("boundary_id", ""),
                "database_source": db.get("permits_2026_source", ""),
                "numeric_comparison_status": numeric_status,
                "semantic_review_flags": "|".join(semantic_flags),
                "review_action": "NO_NUMERIC_ACTION" if numeric_status == "MATCH" else "DO_NOT_OVERWRITE_DATABASE_WITHOUT_REVIEW",
            }
        )
    return comparison


def load_rac_rows() -> dict[str, dict[str, str]]:
    ram_rows, _ = read_csv(RAC_RAM_SOURCE)
    ewe_rows, _ = read_csv(RAC_EWE_SOURCE)
    out: dict[str, dict[str, str]] = {}
    for row in ram_rows:
        if row.get("hunt_code"):
            out[row["hunt_code"]] = row
    for row in ewe_rows:
        if row.get("hunt_code"):
            out[row["hunt_code"]] = row
    return out


def compare_rac(normalized: list[dict[str, str]]) -> list[dict[str, str]]:
    rac_by_code = load_rac_rows()
    comparison: list[dict[str, str]] = []
    for row in normalized:
        code = row["hunt_code"]
        rac = rac_by_code.get(code)
        if rac is None:
            status = "NOT_IN_RAC_COMPARISON_SOURCE"
            rac_res = rac_nr = rac_total = rac_name = ""
        else:
            rac_res = as_int_text(rac.get("permits_2026_res"))
            rac_nr = as_int_text(rac.get("permits_2026_nr"))
            rac_total = as_int_text(rac.get("permits_2026_total"))
            rac_name = rac.get("permit_group") or rac.get("hunt_name", "")
            status = (
                "MATCH"
                if (row["permits_2026_res"], row["permits_2026_nr"], row["permits_2026_total"])
                == (rac_res, rac_nr, rac_total)
                else "RAC_DIFFERENCE"
            )
        comparison.append(
            {
                "hunt_code": code,
                "source_hunt_name": row["hunt_name"],
                "rac_hunt_name": rac_name,
                "source_res": row["permits_2026_res"],
                "source_nr": row["permits_2026_nr"],
                "source_total": row["permits_2026_total"],
                "rac_res": rac_res,
                "rac_nr": rac_nr,
                "rac_total": rac_total,
                "comparison_status": status,
            }
        )
    return comparison


def build_parallel_rows(database_by_code: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for conservation_code, public_codes in CONSERVATION_PUBLIC_PARALLELS.items():
        conservation = database_by_code.get(conservation_code, {})
        public_rows = [database_by_code.get(code, {}) for code in public_codes]
        public_total = sum(int(as_int_text(row.get("permits_2026_total")) or 0) for row in public_rows)
        conservation_total = as_int_text(conservation.get("permits_2026_total"))
        rows.append(
            {
                "conservation_hunt_code": conservation_code,
                "conservation_hunt_name": conservation.get("hunt_name", ""),
                "conservation_total": conservation_total,
                "public_parallel_hunt_codes": "|".join(public_codes),
                "public_parallel_hunt_names": "|".join(row.get("hunt_name", "") for row in public_rows),
                "public_parallel_total": str(public_total),
                "relationship_type": "PARALLEL_CONSERVATION_ROW_TO_PUBLIC_OIAL_UNIT",
                "resolution_status": "RESOLVED_PARALLEL_NOT_REPLACEMENT",
                "notes": (
                    "Conservation/current Rocky Mountain bighorn code is a parallel current permit opportunity, "
                    "not a replacement for the public once-in-a-lifetime row(s)."
                ),
            }
        )
    return rows


def write_report(summary: dict[str, object]) -> None:
    lines = [
        "# 2026 Rocky Mountain Bighorn Permit Audit",
        "",
        "Reviewed current 2026 Rocky Mountain bighorn sheep permit rows against DATABASE.csv and RAC comparison evidence.",
        "",
        f"- Source rows: {summary['source_rows']}",
        f"- Unique RS/RE codes: {summary['unique_hunt_codes']}",
        f"- Numeric total permits carried in reviewed output: {summary['source_total_permits_2026']}",
        f"- DATABASE numeric mismatches: {summary['database_mismatch_count']}",
        f"- RAC numeric mismatches: {summary['rac_mismatch_count']}",
        f"- Rows needing semantic review: {summary['semantic_review_count']}",
        f"- Parallel conservation rows resolved: {summary['parallel_conservation_row_count']}",
        "",
        "The `RS100x` conservation/current rows are parallel opportunities, not replacements for the public/OIAL `RS67xx` rows.",
        "No populated DATABASE.csv numeric cells were changed by this audit.",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    database_by_code = load_database()
    normalized = normalize_source(database_by_code)
    db_comparison = compare_database(normalized, database_by_code)
    rac_comparison = compare_rac(normalized)
    parallel_rows = build_parallel_rows(database_by_code)

    write_csv(REVIEWED_EXPORT, normalized, REVIEWED_FIELDS)
    write_csv(NORMALIZED_OUT, normalized, OUTPUT_FIELDS)
    write_csv(DB_COMPARE_OUT, db_comparison, DB_COMPARE_FIELDS)
    write_csv(RAC_COMPARE_OUT, rac_comparison, RAC_COMPARE_FIELDS)
    write_csv(PARALLEL_OUT, parallel_rows, PARALLEL_FIELDS)

    db_mismatches = [row for row in db_comparison if row["numeric_comparison_status"] != "MATCH"]
    rac_mismatches = [row for row in rac_comparison if row["comparison_status"] == "RAC_DIFFERENCE"]
    semantic_reviews = [row for row in db_comparison if row["semantic_review_flags"]]
    status_counts = Counter(permit_count_status(row) for row in normalized)
    summary = {
        "artifact": "rocky_bighorn_permits_2026_canonical",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_file": SOURCE_FILE_LABEL,
        "source_sha256": sha256(SOURCE),
        "rac_ram_source_file": str(RAC_RAM_SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "rac_ram_source_sha256": sha256(RAC_RAM_SOURCE),
        "rac_ewe_source_file": str(RAC_EWE_SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "rac_ewe_source_sha256": sha256(RAC_EWE_SOURCE),
        "source_rows": len(normalized),
        "unique_hunt_codes": len({row["hunt_code"] for row in normalized}),
        "source_total_permits_2026": sum(int(row["permits_2026_total"] or 0) for row in normalized),
        "status_counts": dict(sorted(status_counts.items())),
        "database_mismatch_count": len(db_mismatches),
        "database_mismatch_codes": [row["hunt_code"] for row in db_mismatches],
        "rac_mismatch_count": len(rac_mismatches),
        "rac_mismatch_codes": [row["hunt_code"] for row in rac_mismatches],
        "semantic_review_count": len(semantic_reviews),
        "semantic_review_codes": [row["hunt_code"] for row in semantic_reviews],
        "parallel_conservation_row_count": len(parallel_rows),
        "parallel_conservation_codes": sorted(CONSERVATION_PUBLIC_PARALLELS),
        "outputs": {
            "reviewed_export": str(REVIEWED_EXPORT.relative_to(ROOT)).replace("\\", "/"),
            "normalized": str(NORMALIZED_OUT.relative_to(ROOT)).replace("\\", "/"),
            "database_comparison": str(DB_COMPARE_OUT.relative_to(ROOT)).replace("\\", "/"),
            "rac_comparison": str(RAC_COMPARE_OUT.relative_to(ROOT)).replace("\\", "/"),
            "parallel_conservation": str(PARALLEL_OUT.relative_to(ROOT)).replace("\\", "/"),
            "report": str(REPORT_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "guardrail": "No populated DATABASE.csv numeric cells were changed by this audit.",
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_report(summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
