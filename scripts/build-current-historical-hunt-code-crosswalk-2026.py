#!/usr/bin/env python3
"""Build the 2026 current-to-historical hunt-code crosswalk truth artifact.

This script intentionally does not change any runtime model inputs. It promotes
the already-created backcheck evidence into a reviewed crosswalk file and checks
that every current/reference code is present in the 2026 DATABASE.csv.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
BACKCHECK_PATH = (
    ROOT
    / "data_model/harvest_quality/raw_packages/unknown_for_unknown_hunt_code_year_backcheck_outputs/"
    / "hunt_code_backward_crosscheck_2026_from_harvest_history.csv"
)
FULL_JOINED_BACKCHECK_PATH = (
    ROOT
    / "data_model/harvest_quality/raw_packages/"
    / "unknown_for_unknown_full_joined_harvest_backcheck_conservation_annual_per_row_corrected/"
    / "full_joined_hunt_code_backcheck_2021_2026_conservation_annual_per_row.csv"
)
OLD_LE_CROSSWALK_PATH = ROOT / "processed_data/historical_le_to_eb_crosswalk_2024.csv"

OVERLAY_LOCK_PATHS = [
    ROOT / "data_truth/permit_overlay_truth/normalized/private_land_deer_hunt_code_lock_2026.csv",
    ROOT / "data_truth/permit_overlay_truth/normalized/conservation_permit_hunt_code_lock_2026.csv",
    ROOT / "data_truth/permit_overlay_truth/normalized/desert_bighorn_conservation_permit_code_lock_2026.csv",
    ROOT / "data_truth/permit_overlay_truth/normalized/final_reference_hunt_code_lock_2026.csv",
]

OUTPUT_PATH = (
    ROOT
    / "data_truth/crosswalk_truth/normalized/current_to_historical_hunt_code_crosswalk_2026.csv"
)
SUMMARY_PATH = (
    ROOT
    / "data_truth/crosswalk_truth/validation/current_to_historical_hunt_code_crosswalk_2026_summary.json"
)
PROCESSED_COPY_PATH = ROOT / "processed_data/current_to_historical_hunt_code_crosswalk_2026.csv"
MARKDOWN_REPORT_PATH = ROOT / "processed_data/current_to_historical_hunt_code_crosswalk_2026.md"

CHANGED_CURRENT_PREFIXES = {"LD", "LP", "EL"}
PINNED_TARGET_CODES = {
    "LO0008",
    "LO0009",
    "LO0010",
    "LO0011",
    "LO0012",
    "LO0013",
    "LO0014",
    "LO0015",
}

PREFIX_SWAP = {
    "LD": "DB",
    "LP": "PB",
    "EL": "EB",
}

PINNED_PRIMARY_CANDIDATES = {
    "RS1001": "RS6701",
    "RS1003": "RS6703",
    "RS1006": "RS6712",
    "DS1002": "DS6601",
    "DS1003": "DS6602|DS6603",
    "DS1004": "DS6608",
    "DS1006": "DS6603",
    "DS1007": "DS6610",
}

OUTPUT_COLUMNS = [
    "current_hunt_code",
    "current_prefix",
    "current_hunt_name",
    "species",
    "sex_type",
    "weapon",
    "hunt_type",
    "season",
    "in_database_2026",
    "database_permits_2026_res",
    "database_permits_2026_nonres",
    "database_permits_2026_total",
    "overlay_source_files",
    "historical_hunt_code",
    "historical_prefix",
    "candidate_historical_codes",
    "historical_years",
    "relationship_type",
    "crosswalk_status",
    "mapping_confidence",
    "mapping_method",
    "data_quality_grade",
    "backcheck_best_match_method",
    "backcheck_reason_code",
    "backcheck_candidates",
    "full_joined_name_match_codes",
    "full_joined_exact_history_years",
    "full_joined_name_match_years",
    "recommended_model_behavior",
    "source_files",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def code_prefix(code: str) -> str:
    match = re.match(r"^([A-Z]+)", code or "")
    return match.group(1) if match else ""


def code_digits(code: str) -> str:
    match = re.search(r"(\d+)$", code or "")
    return match.group(1) if match else ""


def normalized_code_from_row(row: dict[str, str]) -> str:
    for key in ("hunt_code", "Hunt Code", "HUNT_CODE"):
        if row.get(key):
            return row[key].strip()
    return ""


def normalized_field(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row[key].strip()
    return ""


def split_pipe(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split("|") if part.strip()]


def unique_sorted(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(v for v in values if v))


def parse_candidate_codes(candidate_text: str) -> list[str]:
    codes: list[str] = []
    for match in re.finditer(r"\b[A-Z]{1,3}\d{4}\b", candidate_text or ""):
        codes.append(match.group(0))
    return unique_sorted(codes)


def load_database_rows() -> tuple[dict[str, dict[str, str]], set[str]]:
    rows = read_csv(DATABASE_PATH)
    database: dict[str, dict[str, str]] = {}
    for row in rows:
        code = normalized_code_from_row(row)
        if code and code not in database:
            database[code] = row
    return database, set(database)


def load_overlay_codes() -> tuple[set[str], dict[str, set[str]]]:
    overlay_codes: set[str] = set()
    overlay_sources: dict[str, set[str]] = {}
    for path in OVERLAY_LOCK_PATHS:
        for row in read_csv(path):
            code = normalized_code_from_row(row)
            if not code:
                continue
            overlay_codes.add(code)
            overlay_sources.setdefault(code, set()).add(str(path.relative_to(ROOT)).replace("\\", "/"))
    return overlay_codes, overlay_sources


def build_backcheck_indexes() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], dict[str, list[dict[str, str]]]]:
    backcheck = {row["hunt_code"]: row for row in read_csv(BACKCHECK_PATH) if row.get("hunt_code")}
    full_joined = {row["hunt_code"]: row for row in read_csv(FULL_JOINED_BACKCHECK_PATH) if row.get("hunt_code")}
    old_le_rows: dict[str, list[dict[str, str]]] = {}
    for row in read_csv(OLD_LE_CROSSWALK_PATH):
        current_code = row.get("recommended_eb_code", "")
        if current_code:
            old_le_rows.setdefault(current_code, []).append(row)
    return backcheck, full_joined, old_le_rows


def target_current_codes(database_codes: set[str], overlay_codes: set[str]) -> list[str]:
    targets = {code for code in database_codes if code_prefix(code) in CHANGED_CURRENT_PREFIXES}
    targets.update(overlay_codes)
    targets.update(code for code in PINNED_TARGET_CODES if code in database_codes)
    return sorted(targets)


def choose_historical_code(
    current_code: str,
    candidates: list[str],
    database_codes: set[str],
    full_joined_row: dict[str, str],
) -> tuple[str, str, str, str]:
    prefix = code_prefix(current_code)
    digits = code_digits(current_code)

    if prefix in PREFIX_SWAP and digits:
        swapped_code = PREFIX_SWAP[prefix] + digits
        relationship = f"PREFIX_SWAP_{prefix}_TO_{PREFIX_SWAP[prefix]}"
        if swapped_code in candidates:
            return swapped_code, relationship, "PROMOTED_PREFIX_SWAP_CANDIDATE", "HIGH"
        if swapped_code in database_codes:
            return swapped_code, relationship, "PROMOTED_PREFIX_SWAP_CANDIDATE", "MEDIUM"
        return swapped_code, relationship, "PREFIX_SWAP_TARGET_NOT_IN_DATABASE_REVIEW", "LOW"

    if current_code in PINNED_PRIMARY_CANDIDATES:
        primary = PINNED_PRIMARY_CANDIDATES[current_code]
        return primary, "PINNED_HISTORICAL_PUBLIC_OR_CONSERVATION_CANDIDATE", "PROMOTED_PINNED_CANDIDATE", "MEDIUM"

    exact_years = split_pipe(full_joined_row.get("exact_harvest_history_years", ""))
    older_exact_years = [year for year in exact_years if year and year < "2026"]
    if older_exact_years:
        return current_code, "EXACT_CODE_HISTORY", "PROMOTED_EXACT_HISTORY", "HIGH"

    return "", "CURRENT_REFERENCE_ONLY", "CURRENT_REFERENCE_ONLY_NEEDS_REVIEW", "LOW"


def build_rows() -> tuple[list[dict[str, str]], dict[str, object]]:
    database, database_codes = load_database_rows()
    overlay_codes, overlay_sources = load_overlay_codes()
    backcheck, full_joined, old_le_rows = build_backcheck_indexes()
    targets = target_current_codes(database_codes, overlay_codes)

    rows: list[dict[str, str]] = []
    missing_from_database: list[str] = []

    for code in targets:
        db_row = database.get(code, {})
        backcheck_row = backcheck.get(code, {})
        full_joined_row = full_joined.get(code, {})
        old_rows = old_le_rows.get(code, [])

        candidate_codes = unique_sorted(
            parse_candidate_codes(backcheck_row.get("crosswalk_candidates", ""))
            + split_pipe(full_joined_row.get("name_match_hunt_codes", ""))
            + parse_candidate_codes(";".join(row.get("recommended_eb_candidates", "") for row in old_rows))
        )
        historical_code, relationship, status, confidence = choose_historical_code(
            code, candidate_codes, database_codes, full_joined_row
        )
        historical_prefix = "|".join(unique_sorted([code_prefix(part) for part in historical_code.split("|")]))

        if code not in database_codes:
            missing_from_database.append(code)

        source_files = unique_sorted(
            [
                str(DATABASE_PATH.relative_to(ROOT)).replace("\\", "/"),
                str(BACKCHECK_PATH.relative_to(ROOT)).replace("\\", "/") if backcheck_row else "",
                str(FULL_JOINED_BACKCHECK_PATH.relative_to(ROOT)).replace("\\", "/") if full_joined_row else "",
                str(OLD_LE_CROSSWALK_PATH.relative_to(ROOT)).replace("\\", "/") if old_rows else "",
            ]
        )

        notes = []
        if code_prefix(code) in CHANGED_CURRENT_PREFIXES:
            notes.append("Current 2026 Hunt Planner code family is treated as current truth; historical code is a crosswalk candidate, not a replacement.")
        if code in overlay_codes:
            notes.append("Code was independently locked by permit overlay/reference workflow.")
        if status.endswith("NEEDS_REVIEW"):
            notes.append("No dependable older-code mapping was promoted; keep as current reference only.")

        rows.append(
            {
                "current_hunt_code": code,
                "current_prefix": code_prefix(code),
                "current_hunt_name": normalized_field(db_row, "hunt_name", "Hunt Name"),
                "species": normalized_field(db_row, "species", "Species"),
                "sex_type": normalized_field(db_row, "sex_type", "Sex"),
                "weapon": normalized_field(db_row, "weapon", "Weapon"),
                "hunt_type": normalized_field(db_row, "hunt_type", "Hunt Type"),
                "season": normalized_field(db_row, "season", "Season"),
                "in_database_2026": "YES" if code in database_codes else "NO",
                "database_permits_2026_res": normalized_field(db_row, "permits_2026_res", "Res"),
                "database_permits_2026_nonres": normalized_field(db_row, "permits_2026_nr", "Non Res"),
                "database_permits_2026_total": normalized_field(db_row, "permits_2026_total", "Total"),
                "overlay_source_files": "|".join(sorted(overlay_sources.get(code, set()))),
                "historical_hunt_code": historical_code,
                "historical_prefix": historical_prefix,
                "candidate_historical_codes": "|".join(candidate_codes),
                "historical_years": "|".join(
                    unique_sorted(
                        split_pipe(backcheck_row.get("exact_code_history_years", ""))
                        + split_pipe(backcheck_row.get("name_family_match_years", ""))
                        + split_pipe(full_joined_row.get("exact_harvest_history_years", ""))
                        + split_pipe(full_joined_row.get("name_match_history_years", ""))
                    )
                ),
                "relationship_type": relationship,
                "crosswalk_status": status,
                "mapping_confidence": confidence,
                "mapping_method": (
                    "prefix_swap_same_numeric"
                    if relationship.startswith("PREFIX_SWAP")
                    else "pinned_candidate"
                    if relationship.startswith("PINNED")
                    else "exact_history"
                    if relationship == "EXACT_CODE_HISTORY"
                    else "reference_only"
                ),
                "data_quality_grade": full_joined_row.get("data_quality_grade")
                or backcheck_row.get("data_quality_grade", ""),
                "backcheck_best_match_method": backcheck_row.get("best_match_method", ""),
                "backcheck_reason_code": backcheck_row.get("reason_code", ""),
                "backcheck_candidates": backcheck_row.get("crosswalk_candidates", ""),
                "full_joined_name_match_codes": full_joined_row.get("name_match_hunt_codes", ""),
                "full_joined_exact_history_years": full_joined_row.get("exact_harvest_history_years", ""),
                "full_joined_name_match_years": full_joined_row.get("name_match_history_years", ""),
                "recommended_model_behavior": full_joined_row.get("recommended_model_behavior")
                or backcheck_row.get("recommended_model_behavior", ""),
                "source_files": "|".join(source_files),
                "notes": " ".join(notes),
            }
        )

    duplicate_current_codes = [
        code for code, count in Counter(row["current_hunt_code"] for row in rows).items() if count > 1
    ]
    status_counts = Counter(row["crosswalk_status"] for row in rows)
    prefix_counts = Counter(row["current_prefix"] for row in rows)

    blockers = []
    if missing_from_database:
        blockers.append("TARGET_CODES_MISSING_FROM_DATABASE")
    if duplicate_current_codes:
        blockers.append("DUPLICATE_CURRENT_CODE_ROWS")

    summary = {
        "artifact": "current_to_historical_hunt_code_crosswalk_2026",
        "database_source": str(DATABASE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "target_current_code_count": len(targets),
        "output_row_count": len(rows),
        "database_crosscheck_missing_count": len(missing_from_database),
        "database_crosscheck_missing_codes": missing_from_database,
        "duplicate_current_code_count": len(duplicate_current_codes),
        "duplicate_current_codes": duplicate_current_codes,
        "status_counts": dict(sorted(status_counts.items())),
        "prefix_counts": dict(sorted(prefix_counts.items())),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "notes": [
            "This is a crosswalk truth/reference artifact only; it does not rewrite current hunt codes.",
            "Current codes are sourced from DATABASE.csv plus permit overlay locks, then checked back against DATABASE.csv.",
        ],
    }
    return rows, summary


def write_markdown_report(rows: list[dict[str, str]], summary: dict[str, object]) -> None:
    MARKDOWN_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prefix_counts = summary["prefix_counts"]
    status_counts = summary["status_counts"]
    examples = [
        ("LD1001", "private-land deer prefix crosswalk"),
        ("LP5025", "private-land pronghorn prefix crosswalk"),
        ("EL3000", "private-land bull elk prefix crosswalk"),
        ("RS1001", "bighorn conservation candidate"),
        ("BI6527", "exact bison history/reference"),
        ("EX1000", "extended archery reference-only"),
        ("CG9999", "cougar reference-only"),
    ]
    by_code = {row["current_hunt_code"]: row for row in rows}
    lines = [
        "# Current-to-Historical Hunt Code Crosswalk 2026",
        "",
        "This file promotes the older backcheck/crosswalk work into a stable truth artifact.",
        "It is not a runtime rewrite table.",
        "",
        "## Validation",
        "",
        f"- Current target codes: {summary['target_current_code_count']}",
        f"- Output rows: {summary['output_row_count']}",
        f"- Missing from DATABASE.csv: {summary['database_crosscheck_missing_count']}",
        f"- Duplicate current-code rows: {summary['duplicate_current_code_count']}",
        f"- Blockers: {summary['blocker_count']}",
        "",
        "## Prefix Counts",
        "",
    ]
    for prefix, count in sorted(prefix_counts.items()):
        lines.append(f"- {prefix}: {count}")
    lines.extend(["", "## Status Counts", ""])
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Spot Checks", ""])
    for code, label in examples:
        row = by_code.get(code)
        if not row:
            lines.append(f"- {code}: MISSING ({label})")
            continue
        historical = row["historical_hunt_code"] or "(none)"
        lines.append(
            f"- {code}: {historical}; {row['relationship_type']}; {row['crosswalk_status']} ({label})"
        )
    MARKDOWN_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows, summary = build_rows()
    write_csv(OUTPUT_PATH, rows, OUTPUT_COLUMNS)
    write_csv(PROCESSED_COPY_PATH, rows, OUTPUT_COLUMNS)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown_report(rows, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
