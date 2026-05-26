"""Normalize and validate 2026 buck deer permit rows."""

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
LE_SOURCE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_deer_buck_limited_entry.csv"
PRIVATE_SOURCE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_deer_buck_limited_entry_private_lands_only.csv"
RAC_SOURCE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_rac_buck_deer_limited_entry_permits.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"

REVIEWED_LE_EXPORT = (
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 buck deer limited entry reviewed res-nr-total.csv"
)
REVIEWED_PRIVATE_EXPORT = (
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 buck deer private land reviewed res-nr-total.csv"
)
NORMALIZED_OUT = ROOT / "data_truth/permit_overlay_truth/normalized/buck_deer_permits_2026_canonical.csv"
DB_COMPARE_OUT = ROOT / "data_truth/permit_overlay_truth/validation/buck_deer_permits_2026_vs_DATABASE.csv"
RAC_COMPARE_OUT = ROOT / "data_truth/permit_overlay_truth/validation/buck_deer_limited_entry_2026_vs_RAC.csv"
PRIVATE_COMPLETENESS_OUT = (
    ROOT / "data_truth/permit_overlay_truth/validation/buck_deer_private_land_2026_source_completeness.csv"
)
SUMMARY_OUT = ROOT / "data_truth/permit_overlay_truth/validation/buck_deer_permits_2026_summary.json"
REPORT_OUT = ROOT / "processed_data/buck_deer_permits_2026_summary.md"

LE_SOURCE_LABEL = "pipeline/RAW/hunt_unit_database/2026/csv/2026_deer_buck_limited_entry.csv"
PRIVATE_SOURCE_LABEL = (
    "pipeline/RAW/hunt_unit_database/2026/csv/2026_deer_buck_limited_entry_private_lands_only.csv"
)
DATABASE_SOURCE_LABEL = "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"

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
    "database_weapon",
    "hunt_type",
    "database_hunt_type",
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
    "permit_count_status",
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

PRIVATE_EXPECTED_CODES = ["LD1001", "LD1004", "LD1006", "LD1019", "LD1023", "LD1108", "LO0008", "LO0009", "LO0010"]


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


def status_for(res: str, nr: str, total: str) -> str:
    if res != "" and nr != "":
        return "FULL_SPLIT"
    if total != "":
        return "TOTAL_ONLY"
    return "NO_PUBLISHED_NUMERIC_PERMIT"


def normalize_row(
    row: dict[str, str],
    database_by_code: dict[str, dict[str, str]],
    source_file_label: str,
    source_hash: str,
    notes: str = "",
) -> dict[str, str]:
    code = row["hunt_code"]
    db_row = database_by_code.get(code, {})
    res = parse_count(row.get("permits_2026_res", ""))
    nr = parse_count(row.get("permits_2026_nr", ""))
    total = parse_count(row.get("permits_2026_total", ""))
    if total and res != "" and nr != "" and int(total) != int(res) + int(nr):
        raise ValueError(f"Res/NonRes total mismatch for {code}: {res}+{nr}!={total}")
    return {
        "hunt_name": row["hunt_name"],
        "hunt_code": code,
        "boundary_id": db_row.get("boundary_id", ""),
        "hunt_code_mapping_status": "REVIEWED_CURRENT_HUNT_CODE" if db_row else "SOURCE_CODE_NOT_IN_DATABASE",
        "boundary_id_mapping_status": "DATABASE_BOUNDARY_ID" if db_row.get("boundary_id") else "BOUNDARY_ID_MISSING",
        "candidate_hunt_code": code,
        "candidate_boundary_id": db_row.get("boundary_id", ""),
        "sex_type": row["sex_type"],
        "database_sex_type": db_row.get("sex_type", ""),
        "species": row["species"],
        "weapon": row["weapon"],
        "database_weapon": db_row.get("weapon", ""),
        "hunt_type": row["hunt_type"],
        "database_hunt_type": db_row.get("hunt_type", ""),
        "season": row["season"],
        "database_season": db_row.get("season", ""),
        "permits_2026_res": res,
        "permits_2026_nr": nr,
        "permits_2026_total": total,
        "permit_count_status": status_for(res, nr, total),
        "source_file": source_file_label,
        "source_sha256": source_hash,
        "notes": " ".join(part for part in [row.get("NOTES", ""), notes] if part),
    }


def normalize_limited_entry(database_by_code: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows, fields = read_csv(LE_SOURCE)
    if fields != INPUT_FIELDS:
        raise ValueError(f"Unexpected limited-entry buck deer source headers: {fields}")
    source_hash = sha256(LE_SOURCE)
    return [normalize_row(row, database_by_code, LE_SOURCE_LABEL, source_hash) for row in rows]


def normalize_private_land(database_by_code: dict[str, dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows, fields = read_csv(PRIVATE_SOURCE)
    if fields != INPUT_FIELDS:
        raise ValueError(f"Unexpected private-land buck deer source headers: {fields}")
    source_hash = sha256(PRIVATE_SOURCE)
    by_code = {row["hunt_code"]: row for row in rows}
    normalized: list[dict[str, str]] = []
    completeness: list[dict[str, str]] = []
    for code in PRIVATE_EXPECTED_CODES:
        db = database_by_code.get(code, {})
        source_row = by_code.get(code)
        status = "PRESENT_IN_SOURCE"
        note = ""
        if source_row is None:
            status = "SOURCE_FILE_OMITS_EXPECTED_CURRENT_CODE"
            note = "Added to reviewed export from canonical DATABASE.csv and user-provided current DWR Hunt Planner row."
            source_row = {
                "hunt_name": db.get("hunt_name", ""),
                "hunt_code": code,
                "sex_type": db.get("sex_type", ""),
                "species": db.get("species", ""),
                "weapon": db.get("weapon", ""),
                "hunt_type": db.get("hunt_type", ""),
                "season": db.get("season", ""),
                "permits_2026_res": "",
                "permits_2026_nr": "",
                "permits_2026_total": "",
                "NOTES": note,
            }
        normalized.append(normalize_row(source_row, database_by_code, PRIVATE_SOURCE_LABEL, source_hash, note))
        completeness.append(
            {
                "hunt_code": code,
                "hunt_name": source_row["hunt_name"],
                "source_presence_status": status,
                "database_presence_status": "PRESENT_IN_DATABASE" if db else "MISSING_DATABASE_ROW",
                "review_note": note,
            }
        )
    extras = sorted(code for code in by_code if code not in PRIVATE_EXPECTED_CODES)
    for code in extras:
        completeness.append(
            {
                "hunt_code": code,
                "hunt_name": by_code[code].get("hunt_name", ""),
                "source_presence_status": "UNEXPECTED_EXTRA_SOURCE_ROW",
                "database_presence_status": "PRESENT_IN_DATABASE" if code in database_by_code else "MISSING_DATABASE_ROW",
                "review_note": "Source row was not part of the expected limited-entry private-land deer code set.",
            }
        )
    return normalized, completeness


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
                    "review_action": "REVIEW_ADD_CURRENT_BUCK_DEER_ROW",
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
        if row["weapon"] != db.get("weapon", ""):
            semantic_flags.append("WEAPON_REVIEW")
        if row["hunt_type"] != db.get("hunt_type", ""):
            semantic_flags.append("HUNT_TYPE_REVIEW")
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


def compare_rac(le_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rac_rows, _ = read_csv(RAC_SOURCE)
    rac_by_code = {row["hunt_code"]: row for row in rac_rows if row.get("hunt_code")}
    comparison: list[dict[str, str]] = []
    for row in le_rows:
        code = row["hunt_code"]
        rac = rac_by_code.get(code)
        if rac is None:
            status = "NOT_IN_RAC_COMPARISON_SOURCE"
            rac_res = rac_nr = rac_total = rac_name = ""
        else:
            rac_res = as_int_text(rac.get("permits_2026_res"))
            rac_nr = as_int_text(rac.get("permits_2026_nr"))
            rac_total = as_int_text(rac.get("permits_2026_total"))
            rac_name = rac.get("permit_group", "")
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


def validate_unique(rows: list[dict[str, str]]) -> None:
    duplicates = sorted(code for code, count in Counter(row["hunt_code"] for row in rows).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate buck deer hunt codes in normalized output: {duplicates}")


def write_report(summary: dict[str, object]) -> None:
    lines = [
        "# 2026 Buck Deer Permit Audit",
        "",
        "Reviewed 2026 limited-entry and limited-entry private-land buck deer permit rows against DATABASE.csv and RAC comparison evidence.",
        "",
        f"- Limited-entry DB rows: {summary['limited_entry_rows']}",
        f"- Private-land LD/LO rows: {summary['private_land_rows']}",
        f"- Numeric 2026 total permits represented: {summary['source_total_permits_2026']}",
        f"- DATABASE numeric mismatches: {summary['database_mismatch_count']}",
        f"- RAC numeric mismatches: {summary['rac_mismatch_count']}",
        f"- Private-land source omissions repaired in reviewed export: {summary['private_source_omission_count']}",
        "",
        "No populated DATABASE.csv numeric cells were changed by this audit.",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    database_by_code = load_database()
    le_rows = normalize_limited_entry(database_by_code)
    private_rows, private_completeness = normalize_private_land(database_by_code)
    normalized = le_rows + private_rows
    validate_unique(normalized)

    db_comparison = compare_database(normalized, database_by_code)
    rac_comparison = compare_rac(le_rows)

    write_csv(REVIEWED_LE_EXPORT, le_rows, REVIEWED_FIELDS)
    write_csv(REVIEWED_PRIVATE_EXPORT, private_rows, REVIEWED_FIELDS)
    write_csv(NORMALIZED_OUT, normalized, OUTPUT_FIELDS)
    write_csv(DB_COMPARE_OUT, db_comparison, DB_COMPARE_FIELDS)
    write_csv(RAC_COMPARE_OUT, rac_comparison, RAC_COMPARE_FIELDS)
    write_csv(
        PRIVATE_COMPLETENESS_OUT,
        private_completeness,
        ["hunt_code", "hunt_name", "source_presence_status", "database_presence_status", "review_note"],
    )

    db_mismatches = [row for row in db_comparison if row["numeric_comparison_status"] != "MATCH"]
    rac_mismatches = [row for row in rac_comparison if row["comparison_status"] == "RAC_DIFFERENCE"]
    semantic_reviews = [row for row in db_comparison if row["semantic_review_flags"]]
    private_omissions = [
        row for row in private_completeness if row["source_presence_status"] == "SOURCE_FILE_OMITS_EXPECTED_CURRENT_CODE"
    ]
    summary = {
        "artifact": "buck_deer_permits_2026_canonical",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "limited_entry_source_file": LE_SOURCE_LABEL,
        "limited_entry_source_sha256": sha256(LE_SOURCE),
        "private_land_source_file": PRIVATE_SOURCE_LABEL,
        "private_land_source_sha256": sha256(PRIVATE_SOURCE),
        "rac_source_file": str(RAC_SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "rac_source_sha256": sha256(RAC_SOURCE),
        "limited_entry_rows": len(le_rows),
        "private_land_rows": len(private_rows),
        "unique_hunt_codes": len({row["hunt_code"] for row in normalized}),
        "source_total_permits_2026": sum(int(row["permits_2026_total"] or 0) for row in normalized),
        "status_counts": dict(sorted(Counter(row["permit_count_status"] for row in normalized).items())),
        "database_mismatch_count": len(db_mismatches),
        "database_mismatch_codes": [row["hunt_code"] for row in db_mismatches],
        "rac_mismatch_count": len(rac_mismatches),
        "rac_mismatch_codes": [row["hunt_code"] for row in rac_mismatches],
        "semantic_review_count": len(semantic_reviews),
        "semantic_review_codes": [row["hunt_code"] for row in semantic_reviews],
        "private_source_omission_count": len(private_omissions),
        "private_source_omission_codes": [row["hunt_code"] for row in private_omissions],
        "outputs": {
            "reviewed_limited_entry": str(REVIEWED_LE_EXPORT.relative_to(ROOT)).replace("\\", "/"),
            "reviewed_private_land": str(REVIEWED_PRIVATE_EXPORT.relative_to(ROOT)).replace("\\", "/"),
            "normalized": str(NORMALIZED_OUT.relative_to(ROOT)).replace("\\", "/"),
            "database_comparison": str(DB_COMPARE_OUT.relative_to(ROOT)).replace("\\", "/"),
            "rac_comparison": str(RAC_COMPARE_OUT.relative_to(ROOT)).replace("\\", "/"),
            "private_completeness": str(PRIVATE_COMPLETENESS_OUT.relative_to(ROOT)).replace("\\", "/"),
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
