from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CANONICAL_HUNT_MASTER = ROOT / "data/utah/official_downloads_2026/hunt_master_canonical_2026.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
HUNT_MASTER = ROOT / "processed_data/hunt_master_enriched.csv"
POINT_LADDER = ROOT / "processed_data/point_ladder_view.csv"
DRAW_REALITY = ROOT / "processed_data/draw_reality_engine.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"
GAP_SCAN = ROOT / "processed_data/2026_hunt_code_family_gap_scan.csv"

VALIDATION_DIR = ROOT / "data_truth/draw_results_truth/validation"
REPORT_DIR = ROOT / "processed_data"

CODE_RECONCILIATION_CSV = VALIDATION_DIR / "2026_elk_bull_reference_hunt_code_reconciliation.csv"
PROMOTION_DETAIL_CSV = REPORT_DIR / "2026_elk_bull_reference_predictive_v2_reference_promotion.csv"
PROMOTION_JSON = REPORT_DIR / "2026_elk_bull_reference_predictive_v2_reference_promotion_summary.json"
RECONCILIATION_JSON = REPORT_DIR / "2026_elk_bull_reference_hunt_code_reconciliation_summary.json"
RECONCILIATION_MD = REPORT_DIR / "2026_elk_bull_reference_hunt_code_reconciliation.md"

TARGET_PREFIX = "EB"
REFERENCE_MODEL_VERSION = "elk_bull_reference_v1.0.0"
REFERENCE_RULE_VERSION = "utah_elk_bull_reference_code_resolution_v1.0.0"
DATA_CUTOFF_DATE = "2026-05-25"

CURRENT_REFERENCE_CODES = [
    "EB1000",
    "EB1001",
    "EB1002",
    "EB1003",
    "EB1004",
    "EB1005",
    "EB1007",
    "EB1009",
    "EB1010",
    "EB1011",
    "EB1012",
    "EB3128",
    "EB3209",
]

HUNT_NAME_OVERRIDES = {
    "EB1011": "Youth General Season Bull Elk",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def clean_number(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return str(number)


def code_prefix(code: str) -> str:
    match = re.match(r"^[A-Z]+", code or "")
    return match.group(0) if match else ""


def sort_key(row: dict[str, str]) -> tuple[str, int, str]:
    code = row.get("hunt_code", "")
    match = re.match(r"^([A-Z]+)(\d+)$", code)
    if not match:
        return (code_prefix(code), 999999, code)
    return (match.group(1), int(match.group(2)), code)


def current_reference_rows() -> list[dict[str, str]]:
    rows_by_code = {
        row.get("hunt_code", ""): row
        for row in read_rows(CANONICAL_HUNT_MASTER)
        if row.get("hunt_code", "") in CURRENT_REFERENCE_CODES
    }
    missing_source = [code for code in CURRENT_REFERENCE_CODES if code not in rows_by_code]
    if missing_source:
        raise RuntimeError(f"Canonical Hunt Planner source is missing EB codes: {missing_source}")
    rows = []
    for code in sorted(CURRENT_REFERENCE_CODES, key=lambda code: (code[:2], int(code[2:]))):
        row = dict(rows_by_code[code])
        if code in HUNT_NAME_OVERRIDES:
            row["hunt_name"] = HUNT_NAME_OVERRIDES[code]
        rows.append(row)
    return rows


def rows_by_code(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in read_rows(path):
        code = row.get("hunt_code", "").strip()
        if code_prefix(code) != TARGET_PREFIX:
            continue
        grouped.setdefault(code, []).append(row)
    return grouped


def missing_eb_codes_from_gap_scan() -> set[str]:
    if not GAP_SCAN.exists():
        return set(CURRENT_REFERENCE_CODES)
    for row in read_rows(GAP_SCAN):
        if row.get("code_prefix") == TARGET_PREFIX:
            return {code for code in row.get("missing_predictive_v2_codes", "").split(";") if code}
    return set()


def draw_pool_for(source: dict[str, str]) -> str:
    hunt_type = source.get("hunt_type", "")
    hunt_name = source.get("hunt_name", "")
    if hunt_type == "Conservation":
        return "elk_conservation_reference"
    if "Private Lands" in hunt_name:
        return "elk_private_land_reference"
    if "Youth" in hunt_name or source.get("youth_flag", "").upper() == "TRUE":
        return "elk_youth_reference"
    if hunt_type == "Statewide":
        return "elk_statewide_reference"
    return "elk_general_season_reference"


def total_only_value(source: dict[str, str]) -> str:
    if source.get("permit_status") != "TOTAL_ONLY":
        return ""
    return clean_number(source.get("permits_2026_total", ""))


def quota_status(source: dict[str, str]) -> str:
    return "TOTAL_ONLY" if total_only_value(source) else "NO_QUOTA_PUBLISHED"


def build_reference_row(fieldnames: list[str], source: dict[str, str]) -> dict[str, str]:
    row = {fieldname: "" for fieldname in fieldnames}
    status = quota_status(source)
    total = total_only_value(source)
    is_private = "Private Lands" in source.get("hunt_name", "")
    reason = (
        "Promoted from current 2026 DWR Hunt Planner elk bull reference coverage; "
        "no draw odds or probability value was invented."
    )
    row.update(
        {
            "year": "2026",
            "forecast_year": "2026",
            "hunt_code": source["hunt_code"],
            "hunt_name": source.get("hunt_name", ""),
            "species": "Elk",
            "sex_type": "Bull",
            "hunt_type": source.get("hunt_type", ""),
            "hunt_class": source.get("hunt_class", "") or source.get("hunt_type", ""),
            "residency": "Reference Only",
            "points": "0",
            "draw_pool": draw_pool_for(source),
            "source_years_used": "2026",
            "source_year_count": "1",
            "latest_source_year": "2026",
            "earliest_source_year": "2026",
            "source_dataset": "2026_elk_bull_hunt_planner_reference",
            "model_strategy": "ELK_BULL_REFERENCE",
            "draw_system_type": "ELK_BULL_REFERENCE",
            "season_dates": source.get("season", ""),
            "weapon": source.get("weapon", ""),
            "algorithm_status": "ELK_BULL_REFERENCE",
            "target_scope": "TARGET",
            "modeled_by_engine": "False",
            "reason": reason,
            "model_version": REFERENCE_MODEL_VERSION,
            "rule_version": REFERENCE_RULE_VERSION,
            "public_permits_2026": total,
            "quota_source_status": status,
            "quota_source_year": "2026",
            "quota_source_file": "data/utah/official_downloads_2026/hunt_master_canonical_2026.csv",
            "quota_2026_total": total,
            "permit_allotment_2026_total": total,
            "permit_allotment_2026_source": "Utah DWR Hunt Planner",
            "permit_allotment_2026_source_file": "data/utah/official_downloads_2026/hunt_master_canonical_2026.csv",
            "permit_allotment_2026_status": status,
            "data_cutoff_date": DATA_CUTOFF_DATE,
            "reason_codes": f"ELK_BULL_REFERENCE|{status}|NO_DRAW_PROBABILITY_INVENTED",
            "status": "elk_bull_reference_no_draw_odds",
            "trend": "not_modeled",
            "permit_availability_type": draw_pool_for(source),
            "probability_model": "NONE",
            "rule_status": "elk_bull_reference",
            "availability_status": status.lower(),
            "data_quality_flags": f"PROMOTED_ELK_BULL_REFERENCE;NO_DRAW_PROBABILITY_MODELED;{status}",
            "private_lands_allocation_valid": "True" if is_private else "",
            "private_lands_allocation_note": "Uinta Basin private-lands general elk reference row." if is_private else "",
            "private_land_only_flag": "True" if is_private else "False",
            "prediction_year": "2026",
            "source_year": "2026",
            "applicant_forecast_method": "not_modeled_elk_bull_reference",
            "display_odds_text": "Elk bull reference only; odds not modeled",
            "data_quality_grade": "A",
        }
    )
    return row


def promote_missing_reference_rows(source_rows: list[dict[str, str]]) -> dict[str, object]:
    source_by_code = {row["hunt_code"]: row for row in source_rows}
    missing_codes = missing_eb_codes_from_gap_scan()
    predictive_rows = read_rows(PREDICTIVE)
    with PREDICTIVE.open(newline="", encoding="utf-8-sig") as handle:
        fieldnames = csv.DictReader(handle).fieldnames or []

    existing_reference_codes = {
        row.get("hunt_code", "")
        for row in predictive_rows
        if row.get("model_version") == REFERENCE_MODEL_VERSION
    }
    to_promote = sorted(
        code for code in missing_codes if code in source_by_code and code not in existing_reference_codes
    )
    promoted_rows = [build_reference_row(fieldnames, source_by_code[code]) for code in to_promote]
    if promoted_rows:
        predictive_rows.extend(promoted_rows)
        write_rows(PREDICTIVE, fieldnames, predictive_rows)

    final_rows = read_rows(PREDICTIVE)
    reference_rows = [
        row
        for row in final_rows
        if row.get("hunt_code", "") in set(CURRENT_REFERENCE_CODES)
        and row.get("model_version") == REFERENCE_MODEL_VERSION
    ]
    final_reference_codes = {row["hunt_code"] for row in reference_rows}
    still_missing = sorted(code for code in missing_codes if code not in final_reference_codes and code in source_by_code)
    duplicate_keys = [
        key
        for key, count in Counter(
            (
                row.get("hunt_code", ""),
                row.get("residency", ""),
                row.get("points", ""),
                row.get("draw_pool", ""),
                row.get("model_version", ""),
            )
            for row in reference_rows
        ).items()
        if count > 1
    ]
    stale_total_leaks = [
        row["hunt_code"]
        for row in reference_rows
        if row.get("hunt_code", "") in {"EB1001", "EB1002", "EB1003", "EB1004", "EB1005", "EB1009", "EB1010"}
        and (
            row.get("public_permits_2026", "")
            or row.get("quota_2026_total", "")
            or row.get("permit_allotment_2026_total", "")
        )
    ]

    detail_rows = [
        {
            "hunt_code": row.get("hunt_code", ""),
            "hunt_name": row.get("hunt_name", ""),
            "species": row.get("species", ""),
            "sex_type": row.get("sex_type", ""),
            "hunt_type": row.get("hunt_type", ""),
            "weapon": row.get("weapon", ""),
            "season_dates": row.get("season_dates", ""),
            "residency": row.get("residency", ""),
            "non_res": row.get("permit_allotment_2026_nr", ""),
            "res": row.get("permit_allotment_2026_res", ""),
            "total": row.get("permit_allotment_2026_total", ""),
            "quota_status": row.get("permit_allotment_2026_status", ""),
            "promotion_status": "PROMOTED_REFERENCE_ONLY",
            "reason": row.get("reason", ""),
        }
        for row in sorted(reference_rows, key=sort_key)
    ]
    write_rows(
        PROMOTION_DETAIL_CSV,
        [
            "hunt_code",
            "hunt_name",
            "species",
            "sex_type",
            "hunt_type",
            "weapon",
            "season_dates",
            "residency",
            "non_res",
            "res",
            "total",
            "quota_status",
            "promotion_status",
            "reason",
        ],
        detail_rows,
    )

    total_only_codes = sorted(code for code, row in source_by_code.items() if total_only_value(row))
    summary = {
        "classification": "ELK_BULL_REFERENCE_PROMOTION",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_prefix": TARGET_PREFIX,
        "source_reference_hunt_code_count": len(source_by_code),
        "initial_missing_predictive_hunt_codes": sorted(missing_codes),
        "newly_promoted_hunt_code_count": len(promoted_rows),
        "newly_promoted_hunt_codes": [row["hunt_code"] for row in promoted_rows],
        "promoted_reference_hunt_code_count": len(final_reference_codes),
        "still_missing_predictive_hunt_code_count": len(still_missing),
        "still_missing_predictive_hunt_codes": still_missing,
        "gap_scan_hunt_codes_before_refresh": sorted(missing_codes),
        "duplicate_reference_key_count": len(duplicate_keys),
        "stale_database_total_leak_count": len(stale_total_leaks),
        "stale_database_total_leak_codes": stale_total_leaks,
        "total_only_source_hunt_codes": total_only_codes,
        "no_quota_published_source_hunt_codes": sorted(code for code in source_by_code if code not in total_only_codes),
        "guardrail": "EB reference rows preserve canonical Hunt Planner totals only when permit_status is TOTAL_ONLY; stale DATABASE general-season totals are ignored.",
    }
    write_json(PROMOTION_JSON, summary)
    return summary


def build_reconciliation_rows(source_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    database_rows = rows_by_code(DATABASE)
    hunt_master_rows = rows_by_code(HUNT_MASTER)
    point_ladder_rows = rows_by_code(POINT_LADDER)
    draw_reality_rows = rows_by_code(DRAW_REALITY)
    predictive_rows = rows_by_code(PREDICTIVE)

    rows: list[dict[str, object]] = []
    for source in source_rows:
        code = source["hunt_code"]
        current_failure = not (
            code in database_rows
            and code in hunt_master_rows
            and code in point_ladder_rows
            and code in draw_reality_rows
            and code in predictive_rows
        )
        rows.append(
            {
                "hunt_code": code,
                "code_prefix": TARGET_PREFIX,
                "hunt_name": source.get("hunt_name", ""),
                "species": source.get("species", ""),
                "sex_type": source.get("sex_type", ""),
                "hunt_type": source.get("hunt_type", ""),
                "weapon": source.get("weapon", ""),
                "season": source.get("season", ""),
                "non_res": clean_number(source.get("permits_2026_nr", "")),
                "res": clean_number(source.get("permits_2026_res", "")),
                "total": total_only_value(source),
                "permit_status": quota_status(source),
                "database_present": str(code in database_rows).lower(),
                "hunt_master_present": str(code in hunt_master_rows).lower(),
                "point_ladder_present": str(code in point_ladder_rows).lower(),
                "draw_reality_present": str(code in draw_reality_rows).lower(),
                "predictive_v2_present": str(code in predictive_rows).lower(),
                "source_basis": "current_2026_dwr_hunt_planner_elk_bull_reference",
                "current_database_reconciliation_status": "FAIL" if current_failure else "PASS",
            }
        )
    return rows


def main() -> int:
    source_rows = current_reference_rows()
    promotion_summary = promote_missing_reference_rows(source_rows)
    reconciliation_rows = build_reconciliation_rows(source_rows)
    write_rows(
        CODE_RECONCILIATION_CSV,
        [
            "hunt_code",
            "code_prefix",
            "hunt_name",
            "species",
            "sex_type",
            "hunt_type",
            "weapon",
            "season",
            "non_res",
            "res",
            "total",
            "permit_status",
            "database_present",
            "hunt_master_present",
            "point_ladder_present",
            "draw_reality_present",
            "predictive_v2_present",
            "source_basis",
            "current_database_reconciliation_status",
        ],
        reconciliation_rows,
    )

    failures = [
        row
        for row in reconciliation_rows
        if row["current_database_reconciliation_status"] != "PASS"
    ]
    permit_status_counts = Counter(row["permit_status"] for row in reconciliation_rows)
    summary = {
        "classification": "ELK_BULL_REFERENCE_HUNT_CODE_RECONCILIATION",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_prefix": TARGET_PREFIX,
        "source_reference_code_count": len(reconciliation_rows),
        "source_reference_codes": [row["hunt_code"] for row in reconciliation_rows],
        "permit_status_counts": dict(sorted(permit_status_counts.items())),
        "promotion_summary": promotion_summary,
        "current_database_reconciliation_failure_count": len(failures),
        "current_database_reconciliation_failures": [row["hunt_code"] for row in failures],
        "blockers": len(failures)
        + int(promotion_summary["still_missing_predictive_hunt_code_count"])
        + int(promotion_summary["duplicate_reference_key_count"])
        + int(promotion_summary["stale_database_total_leak_count"]),
        "guardrail": "Elk bull EB reference resolution closes current Hunt Planner reference-code coverage without changing website feeds, harvest features, or probability math.",
    }
    write_json(RECONCILIATION_JSON, summary)
    RECONCILIATION_MD.write_text(
        "\n".join(
            [
                "# 2026 Elk Bull Reference Hunt-Code Reconciliation",
                "",
                f"- Current `EB` reference rows checked: `{summary['source_reference_code_count']}`",
                f"- Permit status counts: `{summary['permit_status_counts']}`",
                f"- Newly promoted `EB` reference rows: `{promotion_summary['newly_promoted_hunt_code_count']}`",
                f"- Promoted `EB` reference rows present: `{promotion_summary['promoted_reference_hunt_code_count']}`",
                f"- Still missing predictive rows: `{promotion_summary['still_missing_predictive_hunt_code_count']}`",
                f"- Stale DATABASE total leaks: `{promotion_summary['stale_database_total_leak_count']}`",
                f"- Reconciliation failures: `{summary['current_database_reconciliation_failure_count']}`",
                f"- Blockers: `{summary['blockers']}`",
                "",
                "Guardrail: `NO_QUOTA_PUBLISHED` general-season rows keep blank quota fields; only canonical `TOTAL_ONLY` rows carry totals.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 1 if summary["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
