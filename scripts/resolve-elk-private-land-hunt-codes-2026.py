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

CODE_RECONCILIATION_CSV = VALIDATION_DIR / "2026_elk_private_land_hunt_code_reconciliation.csv"
PROMOTION_DETAIL_CSV = REPORT_DIR / "2026_elk_private_land_predictive_v2_reference_promotion.csv"
PROMOTION_JSON = REPORT_DIR / "2026_elk_private_land_predictive_v2_reference_promotion_summary.json"
RECONCILIATION_JSON = REPORT_DIR / "2026_elk_private_land_hunt_code_reconciliation_summary.json"
RECONCILIATION_MD = REPORT_DIR / "2026_elk_private_land_hunt_code_reconciliation.md"

TARGET_PREFIX = "EL"
REFERENCE_MODEL_VERSION = "elk_private_land_reference_v1.0.0"
REFERENCE_RULE_VERSION = "utah_elk_private_land_code_resolution_v1.0.0"
DATA_CUTOFF_DATE = "2026-05-25"


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


def code_prefix(code: str) -> str:
    match = re.match(r"^[A-Z]+", code or "")
    return match.group(0) if match else ""


def sort_key(row: dict[str, str]) -> tuple[str, int, str]:
    code = row.get("hunt_code", "")
    match = re.match(r"^([A-Z]+)(\d+)$", code)
    if not match:
        return (code_prefix(code), 999999, code)
    return (match.group(1), int(match.group(2)), code)


def current_elk_private_land_rows() -> list[dict[str, str]]:
    rows = []
    for row in read_rows(CANONICAL_HUNT_MASTER):
        if not row.get("hunt_code", "").startswith(TARGET_PREFIX):
            continue
        if row.get("species") != "Elk" or row.get("sex_type") != "Bull":
            continue
        if row.get("hunt_type") != "Limited Entry - Private Land Only":
            continue
        rows.append(row)
    return sorted(rows, key=sort_key)


def current_lo_elk_rows() -> list[dict[str, str]]:
    rows = []
    for row in read_rows(CANONICAL_HUNT_MASTER):
        if not row.get("hunt_code", "").startswith("LO"):
            continue
        if row.get("species") == "Elk" and row.get("sex_type") == "Bull":
            rows.append(row)
    return sorted(rows, key=sort_key)


def rows_by_code(path: Path, prefixes: set[str]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in read_rows(path):
        code = row.get("hunt_code", "").strip()
        if not code or code_prefix(code) not in prefixes:
            continue
        grouped.setdefault(code, []).append(row)
    return grouped


def missing_el_codes_from_gap_scan() -> set[str]:
    if not GAP_SCAN.exists():
        return {row["hunt_code"] for row in current_elk_private_land_rows()}
    for row in read_rows(GAP_SCAN):
        if row.get("code_prefix") == TARGET_PREFIX:
            return {code for code in row.get("missing_predictive_v2_codes", "").split(";") if code}
    return set()


def build_reference_row(fieldnames: list[str], source: dict[str, str]) -> dict[str, str]:
    row = {fieldname: "" for fieldname in fieldnames}
    reason = (
        "Promoted from current 2026 DWR Hunt Planner elk private-land-only reference coverage; "
        "no draw odds, probability or quota value was invented."
    )
    row.update(
        {
            "year": "2026",
            "forecast_year": "2026",
            "hunt_code": source["hunt_code"],
            "hunt_name": source.get("hunt_name", ""),
            "species": "Elk",
            "sex_type": "Bull",
            "hunt_type": "Limited Entry - Private Land Only",
            "hunt_class": "Private Land Only",
            "residency": "Private Land Only",
            "points": "0",
            "draw_pool": "private_land_elk_reference",
            "source_years_used": "2026",
            "source_year_count": "1",
            "latest_source_year": "2026",
            "earliest_source_year": "2026",
            "source_dataset": "2026_elk_private_land_hunt_planner_reference",
            "model_strategy": "ELK_PRIVATE_LAND_REFERENCE",
            "draw_system_type": "PRIVATE_LAND_ELK_REFERENCE",
            "season_dates": source.get("season", ""),
            "weapon": source.get("weapon", ""),
            "algorithm_status": "ELK_PRIVATE_LAND_REFERENCE",
            "target_scope": "TARGET",
            "modeled_by_engine": "False",
            "reason": reason,
            "model_version": REFERENCE_MODEL_VERSION,
            "rule_version": REFERENCE_RULE_VERSION,
            "quota_source_status": "NO_QUOTA_PUBLISHED",
            "quota_source_year": "2026",
            "quota_source_file": "data/utah/official_downloads_2026/hunt_master_canonical_2026.csv",
            "permit_allotment_2026_source": "Utah DWR Hunt Planner",
            "permit_allotment_2026_source_file": "data/utah/official_downloads_2026/hunt_master_canonical_2026.csv",
            "permit_allotment_2026_status": "NO_QUOTA_PUBLISHED",
            "data_cutoff_date": DATA_CUTOFF_DATE,
            "reason_codes": "ELK_PRIVATE_LAND_REFERENCE|NO_QUOTA_PUBLISHED|NO_DRAW_PROBABILITY_INVENTED",
            "status": "elk_private_land_reference_no_draw_odds",
            "trend": "not_modeled",
            "permit_availability_type": "private_land_elk_reference",
            "probability_model": "NONE",
            "rule_status": "elk_private_land_reference",
            "availability_status": "source_confirmed_no_quota_published",
            "data_quality_flags": "PROMOTED_ELK_PRIVATE_LAND_REFERENCE;NO_DRAW_PROBABILITY_MODELED;NO_QUOTA_PUBLISHED",
            "private_lands_allocation_valid": "True",
            "private_lands_allocation_note": "Private-land-only bull elk reference row; no quota published by source.",
            "private_land_only_flag": "True",
            "prediction_year": "2026",
            "source_year": "2026",
            "applicant_forecast_method": "not_modeled_elk_private_land_reference",
            "display_odds_text": "Private-land elk reference only; odds not modeled",
            "data_quality_grade": "A",
        }
    )
    return row


def promote_missing_reference_rows(source_rows: list[dict[str, str]]) -> dict[str, object]:
    source_by_code = {row["hunt_code"]: row for row in source_rows}
    missing_codes = missing_el_codes_from_gap_scan() or set(source_by_code)
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
        if row.get("hunt_code", "").startswith(TARGET_PREFIX)
        and row.get("model_version") == REFERENCE_MODEL_VERSION
    ]
    final_reference_codes = {row["hunt_code"] for row in reference_rows}
    still_missing = sorted(set(source_by_code) - final_reference_codes)
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
            for row in final_rows
            if row.get("hunt_code", "").startswith(TARGET_PREFIX)
        ).items()
        if count > 1
    ]
    quota_leaks = [
        row["hunt_code"]
        for row in reference_rows
        if row.get("public_permits_2026", "")
        or row.get("quota_2026_total", "")
        or row.get("permit_allotment_2026_res", "")
        or row.get("permit_allotment_2026_nr", "")
        or row.get("permit_allotment_2026_total", "")
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
            "promotion_status",
            "reason",
        ],
        detail_rows,
    )

    summary = {
        "classification": "ELK_PRIVATE_LAND_REFERENCE_PROMOTION",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_prefix": TARGET_PREFIX,
        "expected_private_land_hunt_code_count": len(source_by_code),
        "initial_missing_predictive_hunt_codes": sorted(missing_codes),
        "newly_promoted_hunt_code_count": len(promoted_rows),
        "newly_promoted_hunt_codes": [row["hunt_code"] for row in promoted_rows],
        "promoted_reference_hunt_code_count": len(final_reference_codes),
        "still_missing_predictive_hunt_code_count": len(still_missing),
        "still_missing_predictive_hunt_codes": still_missing,
        "duplicate_reference_key_count": len(duplicate_keys),
        "quota_leak_reference_row_count": len(quota_leaks),
        "quota_leak_reference_hunt_codes": quota_leaks,
        "guardrail": "EL private-land elk rows are reference-only; no public EB quota or draw probability values are copied into EL rows.",
    }
    write_json(PROMOTION_JSON, summary)
    return summary


def build_reconciliation_rows(source_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    prefixes = {TARGET_PREFIX}
    database_rows = rows_by_code(DATABASE, prefixes)
    hunt_master_rows = rows_by_code(HUNT_MASTER, prefixes)
    point_ladder_rows = rows_by_code(POINT_LADDER, prefixes)
    draw_reality_rows = rows_by_code(DRAW_REALITY, prefixes)
    predictive_rows = rows_by_code(PREDICTIVE, prefixes)

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
                "non_res": source.get("permits_2026_nr", ""),
                "res": source.get("permits_2026_res", ""),
                "total": source.get("permits_2026_total", ""),
                "permit_status": source.get("permit_status", ""),
                "data_status": source.get("data_status", ""),
                "database_present": str(code in database_rows).lower(),
                "hunt_master_present": str(code in hunt_master_rows).lower(),
                "point_ladder_present": str(code in point_ladder_rows).lower(),
                "draw_reality_present": str(code in draw_reality_rows).lower(),
                "predictive_v2_present": str(code in predictive_rows).lower(),
                "source_basis": "current_2026_dwr_hunt_planner_elk_private_land_reference",
                "current_database_reconciliation_status": "FAIL" if current_failure else "PASS",
            }
        )
    return rows


def main() -> int:
    source_rows = current_elk_private_land_rows()
    lo_elk_rows = current_lo_elk_rows()
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
            "data_status",
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
    weapon_counts = Counter(row["weapon"] for row in source_rows)
    summary = {
        "classification": "ELK_PRIVATE_LAND_HUNT_CODE_RECONCILIATION",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_prefix": TARGET_PREFIX,
        "current_database_code_count": len(reconciliation_rows),
        "current_database_weapon_counts": dict(sorted(weapon_counts.items())),
        "lo_elk_rows_not_promoted_by_this_resolver": [row["hunt_code"] for row in lo_elk_rows],
        "lo_elk_note": "Diamond Mtn LO elk rows are exported with elk private-land references but are not part of the EL prefix gap.",
        "promotion_summary": promotion_summary,
        "current_database_reconciliation_failure_count": len(failures),
        "current_database_reconciliation_failures": [row["hunt_code"] for row in failures],
        "blockers": len(failures)
        + int(promotion_summary["still_missing_predictive_hunt_code_count"])
        + int(promotion_summary["duplicate_reference_key_count"])
        + int(promotion_summary["quota_leak_reference_row_count"]),
        "guardrail": "Elk private-land resolution closes EL hunt-code coverage without changing EB public draw odds, harvest features, or probability math.",
    }
    write_json(RECONCILIATION_JSON, summary)
    RECONCILIATION_MD.write_text(
        "\n".join(
            [
                "# 2026 Elk Private-Land Hunt-Code Reconciliation",
                "",
                f"- Current `EL` private-land bull elk rows checked: `{summary['current_database_code_count']}`",
                f"- Newly promoted `EL` reference rows: `{promotion_summary['newly_promoted_hunt_code_count']}`",
                f"- Promoted `EL` reference rows present: `{promotion_summary['promoted_reference_hunt_code_count']}`",
                f"- Still missing predictive rows: `{promotion_summary['still_missing_predictive_hunt_code_count']}`",
                f"- `EL` quota leaks: `{promotion_summary['quota_leak_reference_row_count']}`",
                f"- Reconciliation failures: `{summary['current_database_reconciliation_failure_count']}`",
                f"- Blockers: `{summary['blockers']}`",
                "",
                "Guardrail: `EL` private-land-only rows are reference-only and do not inherit public `EB` quota or draw-odds values.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 1 if summary["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
