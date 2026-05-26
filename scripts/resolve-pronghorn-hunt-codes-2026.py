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

EXPORT_CSV = REPORT_DIR / "pronghorn_buck_limited_entry_reference_export.csv"
EXPORT_REPORT = REPORT_DIR / "pronghorn_buck_limited_entry_reference_export_report.json"
CODE_RECONCILIATION_CSV = VALIDATION_DIR / "2026_pronghorn_hunt_code_reconciliation.csv"
PROMOTION_DETAIL_CSV = REPORT_DIR / "2026_pronghorn_private_land_predictive_v2_reference_promotion.csv"
PROMOTION_JSON = REPORT_DIR / "2026_pronghorn_private_land_predictive_v2_reference_promotion_summary.json"
RECONCILIATION_JSON = REPORT_DIR / "2026_pronghorn_hunt_code_reconciliation_summary.json"
RECONCILIATION_MD = REPORT_DIR / "2026_pronghorn_hunt_code_reconciliation.md"

TARGET_PREFIXES = {"PB", "LP"}
PRIVATE_LAND_CODES = {"LP5025", "LP5031", "LP5033", "LP5046", "LP5049", "LP5051"}
REFERENCE_MODEL_VERSION = "pronghorn_private_land_reference_v1.0.0"
REFERENCE_RULE_VERSION = "utah_pronghorn_private_land_code_resolution_v1.0.0"
DATA_CUTOFF_DATE = "2026-05-25"

EXPORT_COLUMNS = [
    "Hunt Name",
    "Hunt Code",
    "Sex",
    "Species",
    "Weapon",
    "Hunt Type",
    "Season",
    "Non Res",
    "Res",
    "Total",
    "Source Authority",
    "Permit Status",
    "Data Status",
    "Notes",
]


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
    code = row.get("hunt_code") or row.get("Hunt Code", "")
    match = re.match(r"^([A-Z]+)(\d+)$", code)
    if not match:
        return (code_prefix(code), 999999, code)
    return (match.group(1), int(match.group(2)), code)


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


def pronghorn_rows_from_canonical() -> list[dict[str, str]]:
    rows = []
    for row in read_rows(CANONICAL_HUNT_MASTER):
        code = row.get("hunt_code", "").strip()
        if code_prefix(code) not in TARGET_PREFIXES:
            continue
        if row.get("species", "").strip() != "Pronghorn" or row.get("sex_type", "").strip() != "Buck":
            continue
        rows.append(row)
    return sorted(rows, key=sort_key)


def rows_by_code(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in read_rows(path):
        code = row.get("hunt_code", "").strip()
        if not code or code_prefix(code) not in TARGET_PREFIXES:
            continue
        grouped.setdefault(code, []).append(row)
    return grouped


def export_row(source: dict[str, str]) -> dict[str, str]:
    code = source["hunt_code"]
    is_private = code in PRIVATE_LAND_CODES
    if is_private:
        non_res = res = total = ""
        permit_status = "NO_QUOTA_PUBLISHED"
        data_status = "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED"
        notes = (
            "DWR Hunt Planner source confirmed private-land-only pronghorn row; "
            "no resident, nonresident or total permit allotment is published."
        )
    else:
        non_res = clean_number(source.get("permits_2026_nr", ""))
        res = clean_number(source.get("permits_2026_res", ""))
        total = clean_number(source.get("permits_2026_total", ""))
        permit_status = source.get("permit_status", "")
        data_status = source.get("data_status", "")
        notes = "Published 2026 pronghorn buck reference row from canonical Hunt Planner surface."

    return {
        "Hunt Name": source.get("hunt_name", ""),
        "Hunt Code": code,
        "Sex": source.get("sex_type", ""),
        "Species": source.get("species", ""),
        "Weapon": source.get("weapon", ""),
        "Hunt Type": source.get("hunt_type", ""),
        "Season": source.get("season", ""),
        "Non Res": non_res,
        "Res": res,
        "Total": total,
        "Source Authority": "Utah DWR Hunt Planner",
        "Permit Status": permit_status,
        "Data Status": data_status,
        "Notes": notes,
    }


def build_reference_row(fieldnames: list[str], source: dict[str, str]) -> dict[str, str]:
    row = {fieldname: "" for fieldname in fieldnames}
    reason = (
        "Promoted from current 2026 DWR Hunt Planner pronghorn private-land-only reference coverage; "
        "no draw odds, probability or quota value was invented."
    )
    row.update(
        {
            "year": "2026",
            "forecast_year": "2026",
            "hunt_code": source["hunt_code"],
            "hunt_name": source.get("hunt_name", ""),
            "species": "Pronghorn",
            "sex_type": "Buck",
            "hunt_type": "Limited Entry - Private Land Only",
            "hunt_class": "Private Land Only",
            "residency": "Private Land Only",
            "points": "0",
            "draw_pool": "private_land_pronghorn_reference",
            "source_years_used": "2026",
            "source_year_count": "1",
            "latest_source_year": "2026",
            "earliest_source_year": "2026",
            "source_dataset": "2026_pronghorn_private_land_hunt_planner_reference",
            "model_strategy": "PRONGHORN_PRIVATE_LAND_REFERENCE",
            "draw_system_type": "PRIVATE_LAND_PRONGHORN_REFERENCE",
            "season_dates": source.get("season", ""),
            "weapon": source.get("weapon", ""),
            "algorithm_status": "PRONGHORN_PRIVATE_LAND_REFERENCE",
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
            "reason_codes": "PRONGHORN_PRIVATE_LAND_REFERENCE|NO_QUOTA_PUBLISHED|NO_DRAW_PROBABILITY_INVENTED",
            "status": "pronghorn_private_land_reference_no_draw_odds",
            "trend": "not_modeled",
            "permit_availability_type": "private_land_pronghorn_reference",
            "probability_model": "NONE",
            "rule_status": "pronghorn_private_land_reference",
            "availability_status": "source_confirmed_no_quota_published",
            "data_quality_flags": "PROMOTED_PRONGHORN_PRIVATE_LAND_REFERENCE;NO_DRAW_PROBABILITY_MODELED;NO_QUOTA_PUBLISHED",
            "private_lands_allocation_valid": "True",
            "private_lands_allocation_note": "Private-land-only pronghorn reference row; no quota published by source.",
            "private_land_only_flag": "True",
            "prediction_year": "2026",
            "source_year": "2026",
            "applicant_forecast_method": "not_modeled_pronghorn_private_land_reference",
            "display_odds_text": "Private-land pronghorn reference only; odds not modeled",
            "data_quality_grade": "A",
        }
    )
    return row


def missing_lp_codes_from_gap_scan() -> set[str]:
    if not GAP_SCAN.exists():
        return set(PRIVATE_LAND_CODES)
    missing: set[str] = set()
    for row in read_rows(GAP_SCAN):
        if row.get("code_prefix") != "LP":
            continue
        missing.update(code for code in row.get("missing_predictive_v2_codes", "").split(";") if code)
    return missing


def promote_private_land_rows(canonical_rows: list[dict[str, str]]) -> dict[str, object]:
    source_by_code = {row["hunt_code"]: row for row in canonical_rows if row["hunt_code"] in PRIVATE_LAND_CODES}
    missing_codes = missing_lp_codes_from_gap_scan() or set(PRIVATE_LAND_CODES)
    predictive_rows = read_rows(PREDICTIVE)
    with PREDICTIVE.open(newline="", encoding="utf-8-sig") as handle:
        fieldnames = csv.DictReader(handle).fieldnames or []

    existing_codes = {
        row.get("hunt_code", "")
        for row in predictive_rows
        if row.get("model_version") == REFERENCE_MODEL_VERSION
    }
    to_promote = sorted(
        code for code in missing_codes if code in source_by_code and code not in existing_codes
    )
    promoted_rows = [build_reference_row(fieldnames, source_by_code[code]) for code in to_promote]
    if promoted_rows:
        predictive_rows.extend(promoted_rows)
        write_rows(PREDICTIVE, fieldnames, predictive_rows)

    final_rows = read_rows(PREDICTIVE)
    reference_rows = [
        row
        for row in final_rows
        if row.get("hunt_code", "") in PRIVATE_LAND_CODES
        and row.get("model_version") == REFERENCE_MODEL_VERSION
    ]
    final_reference_codes = {row["hunt_code"] for row in reference_rows}
    still_missing = sorted(PRIVATE_LAND_CODES - final_reference_codes)
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
            if row.get("hunt_code", "") in PRIVATE_LAND_CODES
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
        "classification": "PRONGHORN_PRIVATE_LAND_REFERENCE_PROMOTION",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_prefix": "LP",
        "expected_private_land_hunt_codes": sorted(PRIVATE_LAND_CODES),
        "initial_missing_predictive_hunt_codes": sorted(missing_codes),
        "newly_promoted_hunt_code_count": len(promoted_rows),
        "newly_promoted_hunt_codes": [row["hunt_code"] for row in promoted_rows],
        "promoted_reference_hunt_code_count": len(final_reference_codes),
        "still_missing_predictive_hunt_code_count": len(still_missing),
        "still_missing_predictive_hunt_codes": still_missing,
        "duplicate_reference_key_count": len(duplicate_keys),
        "quota_leak_reference_row_count": len(quota_leaks),
        "quota_leak_reference_hunt_codes": quota_leaks,
        "guardrail": "LP private-land pronghorn rows are reference-only; no public PB quota or draw probability values are copied into LP rows.",
    }
    write_json(PROMOTION_JSON, summary)
    return summary


def build_reconciliation_rows(canonical_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    database_rows = rows_by_code(DATABASE)
    hunt_master_rows = rows_by_code(HUNT_MASTER)
    point_ladder_rows = rows_by_code(POINT_LADDER)
    draw_reality_rows = rows_by_code(DRAW_REALITY)
    predictive_rows = rows_by_code(PREDICTIVE)

    rows: list[dict[str, object]] = []
    for source in canonical_rows:
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
                "code_prefix": code_prefix(code),
                "hunt_name": source.get("hunt_name", ""),
                "species": source.get("species", ""),
                "sex_type": source.get("sex_type", ""),
                "hunt_type": source.get("hunt_type", ""),
                "weapon": source.get("weapon", ""),
                "season": source.get("season", ""),
                "non_res": clean_number(source.get("permits_2026_nr", "")),
                "res": clean_number(source.get("permits_2026_res", "")),
                "total": clean_number(source.get("permits_2026_total", "")),
                "permit_status": source.get("permit_status", ""),
                "data_status": source.get("data_status", ""),
                "database_present": str(code in database_rows).lower(),
                "hunt_master_present": str(code in hunt_master_rows).lower(),
                "point_ladder_present": str(code in point_ladder_rows).lower(),
                "draw_reality_present": str(code in draw_reality_rows).lower(),
                "predictive_v2_present": str(code in predictive_rows).lower(),
                "source_basis": "current_2026_dwr_hunt_planner_private_land_reference"
                if code in PRIVATE_LAND_CODES
                else "current_2026_dwr_hunt_planner_public_pronghorn_reference",
                "current_database_reconciliation_status": "FAIL" if current_failure else "PASS",
            }
        )
    return rows


def build_export(canonical_rows: list[dict[str, str]]) -> dict[str, object]:
    output_rows = [export_row(row) for row in canonical_rows]
    write_rows(EXPORT_CSV, EXPORT_COLUMNS, output_rows)

    prefix_counts = Counter(row["Hunt Code"][:2] for row in output_rows)
    type_counts = Counter(row["Hunt Type"] for row in output_rows)
    lp_rows = [row for row in output_rows if row["Hunt Code"].startswith("LP")]
    lp_quota_leaks = [
        row["Hunt Code"]
        for row in lp_rows
        if row["Non Res"] or row["Res"] or row["Total"]
    ]
    duplicate_codes = [
        code
        for code, count in Counter(row["Hunt Code"] for row in output_rows).items()
        if count > 1
    ]
    report = {
        "classification": "PRONGHORN_BUCK_REFERENCE_EXPORT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS"
        if not lp_quota_leaks and not duplicate_codes and set(prefix_counts) == TARGET_PREFIXES
        else "FAIL",
        "row_count": len(output_rows),
        "prefix_counts": dict(sorted(prefix_counts.items())),
        "hunt_type_counts": dict(sorted(type_counts.items())),
        "duplicate_code_count": len(duplicate_codes),
        "duplicate_codes": duplicate_codes,
        "lp_quota_leak_count": len(lp_quota_leaks),
        "lp_quota_leak_codes": lp_quota_leaks,
        "required_quota_columns": ["Non Res", "Res", "Total"],
        "source_authority": "Utah DWR Hunt Planner",
        "output_csv": str(EXPORT_CSV.relative_to(ROOT)),
        "guardrail": "Public PB rows preserve published quotas; LP private-land rows keep quota columns blank.",
    }
    write_json(EXPORT_REPORT, report)
    return report


def main() -> int:
    canonical_rows = pronghorn_rows_from_canonical()
    export_report = build_export(canonical_rows)
    promotion_summary = promote_private_land_rows(canonical_rows)
    reconciliation_rows = build_reconciliation_rows(canonical_rows)
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
    prefix_counts = Counter(row["code_prefix"] for row in reconciliation_rows)
    summary = {
        "classification": "PRONGHORN_HUNT_CODE_RECONCILIATION",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_prefixes": sorted(TARGET_PREFIXES),
        "current_database_code_count": len(reconciliation_rows),
        "current_database_prefix_counts": dict(sorted(prefix_counts.items())),
        "export_summary": export_report,
        "promotion_summary": promotion_summary,
        "current_database_reconciliation_failure_count": len(failures),
        "current_database_reconciliation_failures": [row["hunt_code"] for row in failures],
        "blockers": len(failures)
        + int(export_report["status"] != "PASS")
        + int(promotion_summary["still_missing_predictive_hunt_code_count"])
        + int(promotion_summary["duplicate_reference_key_count"])
        + int(promotion_summary["quota_leak_reference_row_count"]),
        "guardrail": "Pronghorn resolution closes PB/LP hunt-code coverage without changing public draw odds, harvest features, or probability math.",
    }
    write_json(RECONCILIATION_JSON, summary)
    RECONCILIATION_MD.write_text(
        "\n".join(
            [
                "# 2026 Pronghorn Hunt-Code Reconciliation",
                "",
                f"- Current pronghorn buck rows checked: `{summary['current_database_code_count']}`",
                f"- Prefix counts: `{summary['current_database_prefix_counts']}`",
                f"- Export rows: `{export_report['row_count']}`",
                f"- Promoted LP private-land reference rows: `{promotion_summary['promoted_reference_hunt_code_count']}`",
                f"- Newly promoted this run: `{promotion_summary['newly_promoted_hunt_code_count']}`",
                f"- Still missing predictive rows: `{promotion_summary['still_missing_predictive_hunt_code_count']}`",
                f"- LP quota leaks: `{promotion_summary['quota_leak_reference_row_count']}`",
                f"- Reconciliation failures: `{summary['current_database_reconciliation_failure_count']}`",
                f"- Blockers: `{summary['blockers']}`",
                "",
                "Guardrail: LP private-land-only rows are reference-only and do not inherit public PB quota or draw-odds values.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 1 if summary["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
