"""Audit 2026 private-lands bull elk EL/LO source rows.

The attached Hunt Planner CSV is evidence for current private-land code rows,
but it publishes no permit counts. Most EL rows carry 2025 season dates, while
the LO Diamond Mtn Landowner Association rows carry 2026 dates. This audit
compares the source against DATABASE.csv and RAC EB permit files without
promoting blank source values or prefix-swap RAC values into private-land rows.
"""

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
SOURCE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 l.e. elk.private lands  EL-2025 and LO-2026.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
RAC_FILES = [
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_rac_limited_entry_bull_elk_permits.csv",
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_rac_limited_entry_bull_elk_hamss_and_september_archery_permits.csv",
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_rac_limited_entry_bull_elk_late_archery_permits.csv",
    ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026_elk_bull_conservation_permit.csv",
]

NORMALIZED_OUT = ROOT / "data_truth/permit_overlay_truth/normalized/elk_private_lands_EL_LO_2026_source_audit.csv"
DB_COMPARE_OUT = ROOT / "data_truth/permit_overlay_truth/validation/elk_private_lands_EL_LO_2026_vs_DATABASE.csv"
RAC_CANDIDATES_OUT = ROOT / "data_truth/permit_overlay_truth/validation/elk_private_lands_EL_LO_2026_rac_candidate_matches.csv"
SUMMARY_OUT = ROOT / "data_truth/permit_overlay_truth/validation/elk_private_lands_EL_LO_2026_summary.json"
REPORT_OUT = ROOT / "processed_data/elk_private_lands_EL_LO_2026_audit.md"


NORMALIZED_FIELDS = [
    "hunt_code",
    "prefix",
    "hunt_name",
    "sex_type",
    "species",
    "weapon",
    "hunt_type",
    "season",
    "date_context",
    "source_permits_2026_total",
    "source_status",
    "source_file",
    "source_sha256",
]

DB_COMPARE_FIELDS = [
    "hunt_code",
    "prefix",
    "source_hunt_name",
    "database_hunt_name",
    "date_context",
    "source_total",
    "database_res",
    "database_nr",
    "database_total",
    "database_allotment_total",
    "database_source",
    "comparison_status",
    "review_action",
]

RAC_FIELDS = [
    "source_hunt_code",
    "candidate_rac_hunt_code",
    "match_type",
    "source_hunt_name",
    "rac_hunt_name",
    "source_weapon",
    "rac_weapon",
    "rac_permits_2026_res",
    "rac_permits_2026_nr",
    "rac_permits_2026_total",
    "rac_source_file",
    "promotion_status",
    "notes",
]


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]
        return rows, [(field or "").strip() for field in (reader.fieldnames or [])]


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


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def date_context(season: str) -> str:
    has_2025 = "2025" in season
    has_2026 = "2026" in season
    if has_2025 and has_2026:
        return "CROSSES_2025_2026"
    if has_2026:
        return "HAS_2026_DATE"
    if has_2025:
        return "HAS_2025_DATE_ONLY"
    return "NO_YEAR_IN_SEASON"


def load_source() -> list[dict[str, str]]:
    rows, _ = read_csv(SOURCE)
    source_hash = sha256(SOURCE)
    normalized: list[dict[str, str]] = []
    for row in rows:
        total = row.get("permits_2026_total", "")
        normalized.append(
            {
                "hunt_code": row.get("hunt_code", ""),
                "prefix": row.get("hunt_code", "")[:2],
                "hunt_name": row.get("hunt_name", ""),
                "sex_type": row.get("sex_type", ""),
                "species": row.get("species", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "season": row.get("season", ""),
                "date_context": date_context(row.get("season", "")),
                "source_permits_2026_total": total,
                "source_status": "PUBLISHED_NUMERIC_TOTAL" if total else "NO_PUBLISHED_PERMIT_COUNT",
                "source_file": str(SOURCE.relative_to(ROOT)),
                "source_sha256": source_hash,
            }
        )
    return normalized


def load_database() -> dict[str, dict[str, str]]:
    rows, _ = read_csv(DATABASE)
    return {row.get("hunt_code", ""): row for row in rows}


def load_rac_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in RAC_FILES:
        if not path.exists():
            continue
        loaded, _ = read_csv(path)
        for row in loaded:
            row["_source_file"] = str(path.relative_to(ROOT))
            rows.append(row)
    return rows


def compare_database(source_rows: list[dict[str, str]], db_by_code: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row in source_rows:
        code = row["hunt_code"]
        db = db_by_code.get(code, {})
        source_total = row["source_permits_2026_total"]
        db_total = db.get("permits_2026_total", "")
        db_allotment = db.get("permit_allotment_2026_total", "")
        if not db:
            status = "MISSING_DATABASE_ROW"
            action = "REVIEW_DATABASE_COVERAGE"
        elif source_total and source_total == db_total:
            status = "MATCH"
            action = "NO_CHANGE"
        elif source_total and source_total != db_total:
            status = "NUMERIC_MISMATCH"
            action = "DO_NOT_OVERWRITE_WITHOUT_REVIEW"
        elif db_total or db_allotment:
            status = "DATABASE_HAS_NUMERIC_VALUE_NOT_IN_SOURCE"
            action = "KEEP_DATABASE_PROTECTED_NUMERIC_VALUE_AND_REVIEW_LINEAGE"
        else:
            status = "SOURCE_AND_DATABASE_BLANK"
            action = "NO_PERMIT_NUMBER_PROMOTION"
        output.append(
            {
                "hunt_code": code,
                "prefix": row["prefix"],
                "source_hunt_name": row["hunt_name"],
                "database_hunt_name": db.get("hunt_name", ""),
                "date_context": row["date_context"],
                "source_total": source_total,
                "database_res": db.get("permits_2026_res", ""),
                "database_nr": db.get("permits_2026_nr", ""),
                "database_total": db_total,
                "database_allotment_total": db_allotment,
                "database_source": db.get("permits_2026_source", ""),
                "comparison_status": status,
                "review_action": action,
            }
        )
    return output


def candidate_code_for(source_code: str) -> str:
    if source_code.startswith("EL"):
        return "EB" + source_code[2:]
    return source_code


def build_rac_candidates(source_rows: list[dict[str, str]], rac_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rac_by_code = {row.get("hunt_code", ""): row for row in rac_rows}
    output: list[dict[str, str]] = []
    for row in source_rows:
        source_code = row["hunt_code"]
        exact = rac_by_code.get(source_code)
        prefix_candidate = rac_by_code.get(candidate_code_for(source_code))
        candidates: list[tuple[str, dict[str, str]]] = []
        if exact:
            candidates.append(("EXACT_CODE", exact))
        if prefix_candidate and prefix_candidate is not exact:
            candidates.append(("EL_TO_EB_PREFIX_CANDIDATE", prefix_candidate))
        for match_type, candidate in candidates:
            output.append(
                {
                    "source_hunt_code": source_code,
                    "candidate_rac_hunt_code": candidate.get("hunt_code", ""),
                    "match_type": match_type,
                    "source_hunt_name": row["hunt_name"],
                    "rac_hunt_name": candidate.get("permit_group", candidate.get("hunt_name", "")),
                    "source_weapon": row["weapon"],
                    "rac_weapon": candidate.get("weapon", ""),
                    "rac_permits_2026_res": candidate.get("permits_2026_res", ""),
                    "rac_permits_2026_nr": candidate.get("permits_2026_nr", ""),
                    "rac_permits_2026_total": candidate.get("permits_2026_total", ""),
                    "rac_source_file": candidate.get("_source_file", ""),
                    "promotion_status": "REVIEW_EVIDENCE_ONLY",
                    "notes": "RAC EB public limited-entry value is not promoted into private-land EL/LO rows without reviewed access-class confirmation.",
                }
            )
    return output


def build_report(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# EL/LO Private-Lands Elk 2026 Audit",
            "",
            f"- Source rows: {summary['source_rows']}",
            f"- Prefix counts: {summary['prefix_counts']}",
            f"- Date context counts: {summary['date_context_counts']}",
            f"- Source rows with permit numbers: {summary['source_numeric_rows']}",
            f"- DATABASE rows with numeric values not in source: {summary['database_numeric_not_in_source_count']}",
            f"- RAC exact-code matches: {summary['rac_exact_code_matches']}",
            f"- RAC EL-to-EB prefix candidate matches: {summary['rac_prefix_candidate_matches']}",
            "",
            "No permit numbers were promoted. RAC matches are evidence-only because the attached source is private-land access while RAC rows are public limited-entry `EB` permit recommendations.",
            "",
        ]
    )


def main() -> int:
    source_rows = load_source()
    db_by_code = load_database()
    rac_rows = load_rac_rows()

    db_compare = compare_database(source_rows, db_by_code)
    rac_candidates = build_rac_candidates(source_rows, rac_rows)

    write_csv(NORMALIZED_OUT, source_rows, NORMALIZED_FIELDS)
    write_csv(DB_COMPARE_OUT, db_compare, DB_COMPARE_FIELDS)
    write_csv(RAC_CANDIDATES_OUT, rac_candidates, RAC_FIELDS)

    db_status_counts = Counter(row["comparison_status"] for row in db_compare)
    rac_match_counts = Counter(row["match_type"] for row in rac_candidates)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(SOURCE.relative_to(ROOT)),
        "source_sha256": sha256(SOURCE),
        "source_rows": len(source_rows),
        "prefix_counts": dict(Counter(row["prefix"] for row in source_rows)),
        "date_context_counts": dict(Counter(row["date_context"] for row in source_rows)),
        "source_numeric_rows": sum(1 for row in source_rows if row["source_permits_2026_total"]),
        "database_status_counts": dict(db_status_counts),
        "database_numeric_not_in_source_count": db_status_counts.get("DATABASE_HAS_NUMERIC_VALUE_NOT_IN_SOURCE", 0),
        "database_missing_rows": db_status_counts.get("MISSING_DATABASE_ROW", 0),
        "rac_candidate_rows": len(rac_candidates),
        "rac_exact_code_matches": rac_match_counts.get("EXACT_CODE", 0),
        "rac_prefix_candidate_matches": rac_match_counts.get("EL_TO_EB_PREFIX_CANDIDATE", 0),
        "outputs": {
            "normalized": str(NORMALIZED_OUT.relative_to(ROOT)),
            "database_comparison": str(DB_COMPARE_OUT.relative_to(ROOT)),
            "rac_candidates": str(RAC_CANDIDATES_OUT.relative_to(ROOT)),
            "report": str(REPORT_OUT.relative_to(ROOT)),
        },
        "promotion_decision": "NO_NUMERIC_PROMOTION_FROM_ATTACHED_SOURCE",
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_OUT.write_text(build_report(summary), encoding="utf-8")

    if len(source_rows) != len({row["hunt_code"] for row in source_rows}):
        raise SystemExit("Duplicate EL/LO hunt codes found in source.")
    if summary["source_numeric_rows"] != 0:
        raise SystemExit("Attached EL/LO source unexpectedly contains numeric permit totals.")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
