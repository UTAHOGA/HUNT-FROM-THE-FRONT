"""Normalize and promote 2026 Utah DWR black bear permit splits.

The DWR Hunt Planner black bear CSV stores resident and nonresident values in
the same physical column by using a continuation row for each NonRes value.
This script folds those continuation rows back into one canonical row per BR
hunt code, writes validation artifacts, and promotes reviewed current 2026
permit/allotment values into DATABASE.csv.
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
SOURCE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 black bear permits.csv"
REVIEWED_SOURCE_EXPORT = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 black bear permits reviewed res-nr-total.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
DRAW_RESULTS_LONG = ROOT / "data_truth/draw_results_truth/normalized/draw_results_long.csv"
BR7307_LOCK = ROOT / "data_truth/permit_overlay_truth/normalized/black_bear_conservation_BR7307_lock_2026.csv"

NORMALIZED_OUT = ROOT / "data_truth/permit_overlay_truth/normalized/black_bear_permits_2026_canonical.csv"
DB_COMPARE_OUT = ROOT / "data_truth/permit_overlay_truth/validation/black_bear_permits_2026_vs_DATABASE.csv"
CODE_COMPARE_OUT = ROOT / "data_truth/permit_overlay_truth/validation/black_bear_2026_vs_2025_code_comparison.csv"
SUMMARY_OUT = ROOT / "data_truth/permit_overlay_truth/validation/black_bear_permits_2026_summary.json"
REPORT_OUT = ROOT / "processed_data/black_bear_permits_2026_summary.md"

SOURCE_LABEL = "2026 DWR Hunt Planner black bear permits CSV"
SOURCE_FILE_LABEL = "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/2026 black bear permits.csv"
CONSERVATION_LABEL = "Utah DWR 2025-2027 Conservation Permit Database"
CONSERVATION_FILE_LABEL = "conservation-permit-hunt-table-2025-27.csv"


NORMALIZED_FIELDS = [
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
    "permit_count_status",
    "source_file",
    "source_sha256",
    "source_row_numbers",
    "notes",
]

REVIEWED_SOURCE_EXPORT_FIELDS = [
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
    "source_status",
    "comparison_status",
    "review_action",
]

CODE_COMPARE_FIELDS = [
    "hunt_code",
    "source_2026_status",
    "draw_results_2025_status",
    "database_2026_status",
    "hunt_name_2026",
    "hunt_name_2025",
    "hunt_type_2026",
    "hunt_type_2025",
    "weapon_2026",
    "weapon_2025",
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


def parse_labeled_count(text: str) -> tuple[str | None, int | None]:
    if not text:
        return None, None
    match = re.search(r"\b(Non\s*Res|NonRes|NR|Res)\s*:\s*(\d+)\b", text, flags=re.IGNORECASE)
    if not match:
        return None, None
    label = match.group(1).lower().replace(" ", "")
    value = int(match.group(2))
    if label in {"nonres", "nr"}:
        return "nr", value
    return "res", value


def apply_count(record: dict[str, object], text: str) -> bool:
    label, value = parse_labeled_count(text)
    if label is None or value is None:
        return False
    record[f"permits_2026_{label}"] = str(value)
    return True


def recompute_status(record: dict[str, object]) -> None:
    res = record.get("permits_2026_res", "")
    nr = record.get("permits_2026_nr", "")
    total = record.get("permits_2026_total", "")
    if res != "" or nr != "":
        total_int = int(res or 0) + int(nr or 0)
        record["permits_2026_total"] = str(total_int)
        record["permit_count_status"] = "FULL_SPLIT"
    elif total != "":
        record["permit_count_status"] = "TOTAL_ONLY"
    else:
        record["permit_count_status"] = "NO_PUBLISHED_NUMERIC_PERMIT"


def load_br7307_total() -> str:
    if not BR7307_LOCK.exists():
        return "4"
    rows, _ = read_csv(BR7307_LOCK)
    for row in rows:
        if row.get("hunt_code") == "BR7307" and row.get("permits_2026_total"):
            return row["permits_2026_total"]
    return "4"


def normalize_source() -> list[dict[str, object]]:
    rows, _ = read_csv(SOURCE)
    source_hash = sha256(SOURCE)
    normalized: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for idx, row in enumerate(rows, start=2):
        code = row.get("hunt_code", "")
        if code:
            current = {
                "hunt_name": row.get("hunt_name", ""),
                "hunt_code": code,
                "sex_type": row.get("sex_type", ""),
                "species": row.get("species", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "season": row.get("season", ""),
                "permits_2026_res": "",
                "permits_2026_nr": "",
                "permits_2026_total": "",
                "permit_count_status": "",
                "source_file": SOURCE_FILE_LABEL,
                "source_sha256": source_hash,
                "source_row_numbers": str(idx),
                "notes": "",
            }
            for field in ("permits_2026_res", "permits_2026_nr", "permits_2026_total"):
                apply_count(current, row.get(field, ""))
            normalized.append(current)
            continue

        if current is None:
            continue

        count_applied = False
        for field in ("permits_2026_res", "permits_2026_nr", "permits_2026_total"):
            count_applied = apply_count(current, row.get(field, "")) or count_applied
        if count_applied:
            current["source_row_numbers"] = f"{current['source_row_numbers']};{idx}"
            continue

        season_continuation = row.get("season", "")
        if season_continuation:
            current["season"] = f"{current.get('season', '').strip()} {season_continuation}".strip()
            current["source_row_numbers"] = f"{current['source_row_numbers']};{idx}"

    br7307_total = load_br7307_total()
    for record in normalized:
        if record["hunt_code"] == "BR7307":
            record["permits_2026_res"] = ""
            record["permits_2026_nr"] = ""
            record["permits_2026_total"] = br7307_total
            record["permit_count_status"] = "TOTAL_ONLY"
            record["source_file"] = CONSERVATION_FILE_LABEL
            record["source_sha256"] = sha256(BR7307_LOCK) if BR7307_LOCK.exists() else ""
            record["notes"] = "Conservation package total locked from BR7307 reviewed conservation evidence; no resident/nonresident split published."
        recompute_status(record)

    return normalized


def as_int_text(value: object) -> str:
    text = str(value or "").strip()
    if text == "":
        return ""
    try:
        return str(int(float(text.replace(",", ""))))
    except ValueError:
        return text


def compare_database(normalized: list[dict[str, object]], database_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    db_by_code = {row.get("hunt_code", ""): row for row in database_rows if row.get("hunt_code", "").startswith("BR")}
    comparison: list[dict[str, str]] = []
    for record in normalized:
        code = str(record["hunt_code"])
        db = db_by_code.get(code)
        source_res = as_int_text(record.get("permits_2026_res"))
        source_nr = as_int_text(record.get("permits_2026_nr"))
        source_total = as_int_text(record.get("permits_2026_total"))
        status = str(record.get("permit_count_status", ""))
        if db is None:
            comparison_status = "MISSING_DATABASE_ROW"
            action = "REVIEW_ADD_DATABASE_ROW"
            db_res = db_nr = db_total = db_name = ""
        else:
            db_name = db.get("hunt_name", "")
            db_res = as_int_text(db.get("permits_2026_res"))
            db_nr = as_int_text(db.get("permits_2026_nr"))
            db_total = as_int_text(db.get("permits_2026_total"))
            if status == "NO_PUBLISHED_NUMERIC_PERMIT":
                comparison_status = "NO_NUMERIC_SOURCE"
                action = "KEEP_DATABASE_BLANK_NUMERIC_FIELDS"
            elif (source_res, source_nr, source_total) == (db_res, db_nr, db_total):
                comparison_status = "MATCH"
                action = "NO_NUMERIC_CHANGE"
            else:
                comparison_status = "NUMERIC_MISMATCH"
                action = "PROMOTE_REVIEWED_2026_SOURCE_VALUE"
        comparison.append(
            {
                "hunt_code": code,
                "source_hunt_name": str(record.get("hunt_name", "")),
                "database_hunt_name": db_name,
                "source_res": source_res,
                "source_nr": source_nr,
                "source_total": source_total,
                "database_res": db_res,
                "database_nr": db_nr,
                "database_total": db_total,
                "source_status": status,
                "comparison_status": comparison_status,
                "review_action": action,
            }
        )
    return comparison


def promote_database(normalized: list[dict[str, object]], database_rows: list[dict[str, str]]) -> dict[str, int]:
    by_code = {str(record["hunt_code"]): record for record in normalized}
    counts = Counter()
    for row in database_rows:
        code = row.get("hunt_code", "")
        record = by_code.get(code)
        if not record:
            continue
        status = str(record.get("permit_count_status", ""))
        if status == "NO_PUBLISHED_NUMERIC_PERMIT":
            continue

        res = as_int_text(record.get("permits_2026_res"))
        nr = as_int_text(record.get("permits_2026_nr"))
        total = as_int_text(record.get("permits_2026_total"))
        source = CONSERVATION_LABEL if code == "BR7307" else SOURCE_LABEL
        source_file = CONSERVATION_FILE_LABEL if code == "BR7307" else SOURCE_FILE_LABEL

        for field, value in (
            ("permits_2026_res", res),
            ("permits_2026_nr", nr),
            ("permits_2026_total", total),
            ("permit_allotment_2026_res", res),
            ("permit_allotment_2026_nr", nr),
            ("permit_allotment_2026_total", total),
        ):
            if field in row and as_int_text(row.get(field)) != value:
                row[field] = value
                counts["numeric_cells_changed"] += 1

        for field, value in (
            ("permits_2026_source", source),
            ("permit_allotment_2026_source", source),
            ("permit_allotment_2026_source_file", source_file),
            ("permit_allotment_2026_status", status),
        ):
            if field in row and row.get(field, "") != value:
                row[field] = value
                counts["source_cells_changed"] += 1

        counts["rows_promoted"] += 1
    return dict(counts)


def write_database(rows: list[dict[str, str]], fields: list[str]) -> None:
    with DATABASE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_2025_br_universe() -> dict[str, dict[str, str]]:
    if not DRAW_RESULTS_LONG.exists():
        return {}
    rows, _ = read_csv(DRAW_RESULTS_LONG)
    universe: dict[str, dict[str, str]] = {}
    for row in rows:
        code = row.get("hunt_code", "")
        if not code.startswith("BR") or row.get("year") != "2025":
            continue
        universe.setdefault(code, row)
    return universe


def build_code_comparison(normalized: list[dict[str, object]], database_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    source_by_code = {str(row["hunt_code"]): row for row in normalized}
    db_by_code = {row.get("hunt_code", ""): row for row in database_rows if row.get("hunt_code", "").startswith("BR")}
    prior_by_code = load_2025_br_universe()
    all_codes = sorted(set(source_by_code) | set(db_by_code) | set(prior_by_code))
    output: list[dict[str, str]] = []
    for code in all_codes:
        src = source_by_code.get(code)
        prior = prior_by_code.get(code)
        db = db_by_code.get(code)
        output.append(
            {
                "hunt_code": code,
                "source_2026_status": "PRESENT" if src else "MISSING",
                "draw_results_2025_status": "PRESENT" if prior else "MISSING",
                "database_2026_status": "PRESENT" if db else "MISSING",
                "hunt_name_2026": str((src or {}).get("hunt_name", "")),
                "hunt_name_2025": (prior or {}).get("hunt_name", ""),
                "hunt_type_2026": str((src or {}).get("hunt_type", "")),
                "hunt_type_2025": (prior or {}).get("hunt_type", ""),
                "weapon_2026": str((src or {}).get("weapon", "")),
                "weapon_2025": (prior or {}).get("weapon", ""),
            }
        )
    return output


def build_report(summary: dict[str, object]) -> str:
    missing_2025 = summary["code_comparison"]["codes_present_2026_missing_2025"]
    retired_2025 = summary["code_comparison"]["codes_present_2025_missing_2026"]
    return "\n".join(
        [
            "# 2026 Black Bear Permit Normalization",
            "",
            f"- Normalized BR rows: {summary['normalized_rows']}",
            f"- Numeric FULL_SPLIT rows: {summary['status_counts'].get('FULL_SPLIT', 0)}",
            f"- TOTAL_ONLY rows: {summary['status_counts'].get('TOTAL_ONLY', 0)}",
            f"- NO_PUBLISHED_NUMERIC_PERMIT rows: {summary['status_counts'].get('NO_PUBLISHED_NUMERIC_PERMIT', 0)}",
            f"- DATABASE numeric mismatches after promotion: {summary['database_after_promotion']['numeric_mismatch_count']}",
            f"- DATABASE missing rows after promotion: {summary['database_after_promotion']['missing_database_count']}",
            f"- Reviewed res/nr/total export: `{summary['outputs']['reviewed_source_export']}`",
            f"- 2026 codes missing from 2025 draw-results BR universe: {len(missing_2025)}",
            f"- 2025 draw-results BR codes missing from 2026 source: {len(retired_2025)}",
            "",
            "## 2026 Codes Missing From 2025 BR Draw Results",
            "",
            ", ".join(missing_2025) if missing_2025 else "None",
            "",
            "## 2025 BR Draw Result Codes Missing From 2026 Source",
            "",
            ", ".join(retired_2025) if retired_2025 else "None",
            "",
        ]
    )


def main() -> int:
    normalized = normalize_source()
    duplicate_codes = [code for code, count in Counter(str(row["hunt_code"]) for row in normalized).items() if count > 1]
    if duplicate_codes:
        raise SystemExit(f"Duplicate normalized BR hunt codes: {duplicate_codes}")

    db_rows, db_fields = read_csv(DATABASE)
    before_compare = compare_database(normalized, db_rows)
    promotion_counts = promote_database(normalized, db_rows)
    write_database(db_rows, db_fields)
    after_compare = compare_database(normalized, db_rows)
    code_compare = build_code_comparison(normalized, db_rows)

    write_csv(NORMALIZED_OUT, normalized, NORMALIZED_FIELDS)
    write_csv(REVIEWED_SOURCE_EXPORT, normalized, REVIEWED_SOURCE_EXPORT_FIELDS)
    write_csv(DB_COMPARE_OUT, after_compare, DB_COMPARE_FIELDS)
    write_csv(CODE_COMPARE_OUT, code_compare, CODE_COMPARE_FIELDS)

    status_counts = Counter(str(row.get("permit_count_status", "")) for row in normalized)
    before_status_counts = Counter(row["comparison_status"] for row in before_compare)
    after_status_counts = Counter(row["comparison_status"] for row in after_compare)
    missing_2025 = [row["hunt_code"] for row in code_compare if row["source_2026_status"] == "PRESENT" and row["draw_results_2025_status"] == "MISSING"]
    retired_2025 = [row["hunt_code"] for row in code_compare if row["draw_results_2025_status"] == "PRESENT" and row["source_2026_status"] == "MISSING"]

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": SOURCE_FILE_LABEL,
        "source_sha256": sha256(SOURCE),
        "normalized_rows": len(normalized),
        "unique_hunt_codes": len({str(row["hunt_code"]) for row in normalized}),
        "status_counts": dict(status_counts),
        "database_before_promotion": {
            "status_counts": dict(before_status_counts),
            "numeric_mismatch_count": before_status_counts.get("NUMERIC_MISMATCH", 0),
            "missing_database_count": before_status_counts.get("MISSING_DATABASE_ROW", 0),
        },
        "database_after_promotion": {
            "status_counts": dict(after_status_counts),
            "numeric_mismatch_count": after_status_counts.get("NUMERIC_MISMATCH", 0),
            "missing_database_count": after_status_counts.get("MISSING_DATABASE_ROW", 0),
        },
        "promotion_counts": promotion_counts,
        "code_comparison": {
            "comparison_rows": len(code_compare),
            "codes_present_2026_missing_2025": missing_2025,
            "codes_present_2025_missing_2026": retired_2025,
        },
        "outputs": {
            "normalized": str(NORMALIZED_OUT.relative_to(ROOT)),
            "reviewed_source_export": str(REVIEWED_SOURCE_EXPORT.relative_to(ROOT)),
            "database_comparison": str(DB_COMPARE_OUT.relative_to(ROOT)),
            "code_comparison": str(CODE_COMPARE_OUT.relative_to(ROOT)),
            "report": str(REPORT_OUT.relative_to(ROOT)),
        },
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_OUT.write_text(build_report(summary), encoding="utf-8")

    if after_status_counts.get("MISSING_DATABASE_ROW", 0) or after_status_counts.get("NUMERIC_MISMATCH", 0):
        raise SystemExit("Black bear DATABASE comparison still has blockers after promotion.")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
