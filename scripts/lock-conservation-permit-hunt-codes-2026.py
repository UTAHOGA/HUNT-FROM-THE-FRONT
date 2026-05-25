from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
HUNT_MASTER = ROOT / "processed_data/hunt_master_enriched.csv"
DRAW_REALITY = ROOT / "processed_data/draw_reality_engine.csv"
POINT_LADDER = ROOT / "processed_data/point_ladder_view.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"

LOCK_CSV = ROOT / "data_truth/permit_overlay_truth/normalized/conservation_permit_hunt_code_lock_2026.csv"
SUMMARY_JSON = ROOT / "processed_data/conservation_permit_hunt_code_lock_2026_summary.json"
REPORT_MD = ROOT / "processed_data/conservation_permit_hunt_code_lock_2026.md"
RUNTIME_UPDATES_CSV = ROOT / "processed_data/conservation_permit_hunt_code_lock_2026_runtime_updates.csv"

DATA_CUTOFF_DATE = "2026-05-25"

ANTLERLESS_NO_QUOTA_NOTE = (
    "Utah DWR Hunt Planner source confirms conservation antlerless elk hunt; "
    "no quota or resident/nonresident split was published in the uploaded source."
)
ELK_BULL_TOTAL_ONLY_NOTE = (
    "Total count applied from Utah DWR 2025-2027 Multi-Year Conservation Permit working list. "
    "Resident/nonresident split is not published for these conservation permits."
)

LOCK_ROWS: list[dict[str, str]] = [
    {
        "hunt_code": "EA1180",
        "hunt_name": "La Sal (Conservation)",
        "species": "Elk",
        "sex_type": "Antlerless",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Conservation",
        "season": "Oct 4 - Oct 16, 2025 & Nov 17 - Dec 31, 2025",
        "res": "",
        "non_res": "",
        "total": "",
        "permit_status": "NO_QUOTA_PUBLISHED",
        "permit_allocation_type": "NO_QUOTA_PUBLISHED",
        "permit_source_authority": "Utah DWR Hunt Planner",
        "permit_overlay_source": "2026_elk_antlerless__total.xlsx",
        "data_status": "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED",
        "model_version": "antlerless_reference_v1.0.0",
        "rule_version": "utah_conservation_permit_code_lock_v1.0.0",
        "note": ANTLERLESS_NO_QUOTA_NOTE,
    },
    {
        "hunt_code": "EA1270",
        "hunt_name": "Fishlake (Conservation)",
        "species": "Elk",
        "sex_type": "Antlerless",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Conservation",
        "season": "Oct 4 - Oct 16, 2025 & Nov 22 - Dec 31, 2025",
        "res": "",
        "non_res": "",
        "total": "",
        "permit_status": "NO_QUOTA_PUBLISHED",
        "permit_allocation_type": "NO_QUOTA_PUBLISHED",
        "permit_source_authority": "Utah DWR Hunt Planner",
        "permit_overlay_source": "2026_elk_antlerless__total.xlsx",
        "data_status": "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED",
        "model_version": "antlerless_reference_v1.0.0",
        "rule_version": "utah_conservation_permit_code_lock_v1.0.0",
        "note": ANTLERLESS_NO_QUOTA_NOTE,
    },
    {
        "hunt_code": "EA1271",
        "hunt_name": "Manti (Conservation)",
        "species": "Elk",
        "sex_type": "Antlerless",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Conservation",
        "season": "Oct 4 - Oct 16, 2025 & Nov 19, 2025 - Jan 31, 2026",
        "res": "",
        "non_res": "",
        "total": "",
        "permit_status": "NO_QUOTA_PUBLISHED",
        "permit_allocation_type": "NO_QUOTA_PUBLISHED",
        "permit_source_authority": "Utah DWR Hunt Planner",
        "permit_overlay_source": "2026_elk_antlerless__total.xlsx",
        "data_status": "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED",
        "model_version": "antlerless_reference_v1.0.0",
        "rule_version": "utah_conservation_permit_code_lock_v1.0.0",
        "note": ANTLERLESS_NO_QUOTA_NOTE,
    },
    {
        "hunt_code": "EA2041",
        "hunt_name": "Cache (Conservation)",
        "species": "Elk",
        "sex_type": "Antlerless",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Conservation",
        "season": "Oct 4 - Oct 26, 2025",
        "res": "",
        "non_res": "",
        "total": "",
        "permit_status": "NO_QUOTA_PUBLISHED",
        "permit_allocation_type": "NO_QUOTA_PUBLISHED",
        "permit_source_authority": "Utah DWR Hunt Planner",
        "permit_overlay_source": "2026_elk_antlerless__total.xlsx",
        "data_status": "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED",
        "model_version": "antlerless_reference_v1.0.0",
        "rule_version": "utah_conservation_permit_code_lock_v1.0.0",
        "note": ANTLERLESS_NO_QUOTA_NOTE,
    },
    {
        "hunt_code": "EA2045",
        "hunt_name": "Wasatch Mtns (Conservation)",
        "species": "Elk",
        "sex_type": "Antlerless",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Conservation",
        "season": "Oct 4 - Oct 16, 2025 & Nov 15, 2025 - Jan 31, 2026",
        "res": "",
        "non_res": "",
        "total": "",
        "permit_status": "NO_QUOTA_PUBLISHED",
        "permit_allocation_type": "NO_QUOTA_PUBLISHED",
        "permit_source_authority": "Utah DWR Hunt Planner",
        "permit_overlay_source": "2026_elk_antlerless__total.xlsx",
        "data_status": "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED",
        "model_version": "antlerless_reference_v1.0.0",
        "rule_version": "utah_conservation_permit_code_lock_v1.0.0",
        "note": ANTLERLESS_NO_QUOTA_NOTE,
    },
    {
        "hunt_code": "EB3128",
        "hunt_name": "Box Elder, Grouse Creek",
        "species": "Elk",
        "sex_type": "Bull",
        "weapon": "Multiseason",
        "hunt_type": "Conservation",
        "season": "Any Legal Weapon: Sept 16-20, 2026 & Oct 3 - 15, 2026 | Muzz: Sept 21-Oct 2, 2026",
        "res": "",
        "non_res": "",
        "total": "1",
        "permit_status": "TOTAL_ONLY",
        "permit_allocation_type": "CONSERVATION_MULTIYEAR_TOTAL",
        "permit_source_authority": "Utah DWR Conservation Permit Working List",
        "permit_overlay_source": "8C1294DD__2025-27_conservation_permits.pdf",
        "data_status": "COMPLETE_TOTAL_ONLY",
        "model_version": "elk_bull_reference_v1.0.0",
        "rule_version": "utah_conservation_permit_code_lock_v1.0.0",
        "note": ELK_BULL_TOTAL_ONLY_NOTE,
    },
    {
        "hunt_code": "EB3209",
        "hunt_name": "Box Elder, Pilot Mtn",
        "species": "Elk",
        "sex_type": "Bull",
        "weapon": "Multiseason",
        "hunt_type": "Conservation",
        "season": "Archery: Aug 15-Sept 6, 2026 | Any Legal Weapon: Sept 12-Oct 2, 2026",
        "res": "",
        "non_res": "",
        "total": "1",
        "permit_status": "TOTAL_ONLY",
        "permit_allocation_type": "CONSERVATION_MULTIYEAR_TOTAL",
        "permit_source_authority": "Utah DWR Conservation Permit Working List",
        "permit_overlay_source": "8C1294DD__2025-27_conservation_permits.pdf",
        "data_status": "COMPLETE_TOTAL_ONLY",
        "model_version": "elk_bull_reference_v1.0.0",
        "rule_version": "utah_conservation_permit_code_lock_v1.0.0",
        "note": ELK_BULL_TOTAL_ONLY_NOTE,
    },
]

LOCK_BY_CODE = {row["hunt_code"]: row for row in LOCK_ROWS}
LOCK_CODES = set(LOCK_BY_CODE)


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]], lineterminator: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator=lineterminator,
        )
        writer.writeheader()
        writer.writerows(rows)


def set_if_present(row: dict[str, str], field: str, value: str) -> None:
    if field in row:
        row[field] = value


def snapshot(row: dict[str, str]) -> str:
    fields = [
        "hunt_name",
        "species",
        "sex_type",
        "weapon",
        "hunt_type",
        "season",
        "season_dates",
        "public_permits_2026",
        "permits_2026_res",
        "permits_2026_nr",
        "permits_2026_total",
        "quota_2026_total",
        "permit_allotment_2026_total",
        "permit_status",
        "permit_allotment_2026_status",
        "data_status",
    ]
    return json.dumps({field: row.get(field, "") for field in fields if field in row}, sort_keys=True)


def common_updates(row: dict[str, str], lock: dict[str, str]) -> None:
    set_if_present(row, "hunt_name", lock["hunt_name"])
    set_if_present(row, "species", lock["species"])
    set_if_present(row, "sex_type", lock["sex_type"])
    set_if_present(row, "weapon", lock["weapon"])
    set_if_present(row, "hunt_type", lock["hunt_type"])
    set_if_present(row, "season", lock["season"])
    set_if_present(row, "season_dates", lock["season"])
    set_if_present(row, "permits_2026_res", lock["res"])
    set_if_present(row, "permits_2026_nr", lock["non_res"])
    set_if_present(row, "permits_2026_total", lock["total"])
    set_if_present(row, "public_permits_2026", lock["total"])
    set_if_present(row, "quota_2026_total", lock["total"])
    set_if_present(row, "permit_allotment_2026_res", lock["res"])
    set_if_present(row, "permit_allotment_2026_nr", lock["non_res"])
    set_if_present(row, "permit_allotment_2026_total", lock["total"])
    set_if_present(row, "permit_status", lock["permit_status"])
    set_if_present(row, "permit_allocation_type", lock["permit_allocation_type"])
    set_if_present(row, "permit_source_authority", lock["permit_source_authority"])
    set_if_present(row, "permit_note", lock["note"])
    set_if_present(row, "permit_overlay_source", lock["permit_overlay_source"])
    set_if_present(row, "data_status", lock["data_status"])
    set_if_present(row, "permit_allotment_2026_status", lock["permit_status"])
    set_if_present(row, "permit_allotment_2026_source", lock["permit_source_authority"])
    set_if_present(row, "permit_allotment_2026_source_file", lock["permit_overlay_source"])
    set_if_present(row, "quota_source_status", lock["permit_status"])
    set_if_present(row, "quota_source_file", lock["permit_overlay_source"])
    set_if_present(row, "quota_source_year", "2026")
    set_if_present(row, "public_permits_2026_source", lock["permit_source_authority"] if lock["total"] else "")
    set_if_present(row, "permits_2026_source", lock["permit_source_authority"])
    set_if_present(row, "quota_source", lock["permit_source_authority"])
    set_if_present(row, "permit_source", lock["permit_source_authority"])
    set_if_present(row, "truth_source_file", lock["permit_overlay_source"])
    set_if_present(row, "truth_source_status", lock["data_status"])
    set_if_present(row, "data_cutoff_date", DATA_CUTOFF_DATE)


def runtime_row_updates(row: dict[str, str], lock: dict[str, str]) -> None:
    common_updates(row, lock)
    if lock["permit_status"] == "NO_QUOTA_PUBLISHED":
        set_if_present(row, "missing_permits", "TRUE")
        set_if_present(row, "availability_status", "no_quota_published")
    else:
        set_if_present(row, "missing_permits", "FALSE")
        set_if_present(row, "availability_status", "total_only")


def predictive_updates(row: dict[str, str], lock: dict[str, str]) -> None:
    common_updates(row, lock)
    if lock["sex_type"] == "Antlerless":
        set_if_present(row, "hunt_class", "Antlerless Reference")
        set_if_present(row, "residency", "Resident")
        set_if_present(row, "points", "0")
        set_if_present(row, "draw_pool", "antlerless_reference")
        set_if_present(row, "model_strategy", "ANTLERLESS_REFERENCE")
        set_if_present(row, "draw_system_type", "PREFERENCE_ANTLERLESS_ELK_REFERENCE")
        set_if_present(row, "algorithm_status", "ANTLERLESS_REFERENCE")
        set_if_present(row, "model_version", "antlerless_reference_v1.0.0")
        set_if_present(row, "rule_version", "utah_conservation_permit_code_lock_v1.0.0")
        set_if_present(row, "reason_codes", "CONSERVATION_CODE_LOCK|NO_QUOTA_PUBLISHED|NO_DRAW_PROBABILITY_INVENTED")
        set_if_present(row, "status", "antlerless_reference_no_draw_odds")
        set_if_present(row, "permit_availability_type", "antlerless_conservation_reference")
        set_if_present(row, "rule_status", "antlerless_reference")
        set_if_present(row, "availability_status", "no_quota_published")
        set_if_present(row, "display_odds_text", "Antlerless conservation reference only; odds not modeled")
    else:
        set_if_present(row, "hunt_class", "Conservation")
        set_if_present(row, "residency", "Reference Only")
        set_if_present(row, "points", "0")
        set_if_present(row, "draw_pool", "elk_conservation_reference")
        set_if_present(row, "model_strategy", "ELK_BULL_REFERENCE")
        set_if_present(row, "draw_system_type", "ELK_BULL_REFERENCE")
        set_if_present(row, "algorithm_status", "ELK_BULL_REFERENCE")
        set_if_present(row, "model_version", "elk_bull_reference_v1.0.0")
        set_if_present(row, "rule_version", "utah_conservation_permit_code_lock_v1.0.0")
        set_if_present(row, "reason_codes", "CONSERVATION_CODE_LOCK|TOTAL_ONLY|NO_DRAW_PROBABILITY_INVENTED")
        set_if_present(row, "status", "elk_bull_reference_no_draw_odds")
        set_if_present(row, "permit_availability_type", "elk_conservation_reference")
        set_if_present(row, "rule_status", "elk_bull_reference")
        set_if_present(row, "availability_status", "total_only")
        set_if_present(row, "display_odds_text", "Elk bull reference only; odds not modeled")

    set_if_present(row, "source_years_used", "2026")
    set_if_present(row, "source_year_count", "1")
    set_if_present(row, "latest_source_year", "2026")
    set_if_present(row, "earliest_source_year", "2026")
    set_if_present(row, "source_dataset", "2026_conservation_permit_hunt_code_lock")
    set_if_present(row, "target_scope", "TARGET")
    set_if_present(row, "modeled_by_engine", "False")
    set_if_present(row, "reason", lock["note"] + " No draw odds or probability value was invented.")
    set_if_present(row, "probability_model", "NONE")
    set_if_present(row, "data_quality_flags", f"CONSERVATION_CODE_LOCK;NO_DRAW_PROBABILITY_MODELED;{lock['permit_status']}")
    set_if_present(row, "prediction_year", "2026")
    set_if_present(row, "source_year", "2026")
    set_if_present(row, "applicant_forecast_method", "not_modeled_conservation_reference")
    set_if_present(row, "data_quality_grade", "A")


def update_file(path: Path, updater) -> dict[str, object]:
    fieldnames, rows = read_rows(path)
    touched = 0
    changed = 0
    updates: list[dict[str, str]] = []
    for row in rows:
        code = row.get("hunt_code", "").strip()
        if code not in LOCK_BY_CODE:
            continue
        touched += 1
        before = snapshot(row)
        updater(row, LOCK_BY_CODE[code])
        after = snapshot(row)
        if before != after:
            changed += 1
        updates.append(
            {
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "hunt_code": code,
                "changed": "TRUE" if before != after else "FALSE",
                "before": before,
                "after": after,
            }
        )
    lineterminator = "\n" if path == DATABASE else "\r\n"
    write_rows(path, fieldnames, rows, lineterminator=lineterminator)
    return {"path": path, "row_count": len(rows), "touched": touched, "changed": changed, "updates": updates}


def write_lock_csv() -> None:
    fieldnames = [
        "hunt_code",
        "hunt_name",
        "species",
        "sex_type",
        "weapon",
        "hunt_type",
        "season",
        "Non Res",
        "Res",
        "Total",
        "permit_status",
        "permit_allocation_type",
        "permit_source_authority",
        "permit_overlay_source",
        "data_status",
        "model_version",
        "rule_version",
        "note",
    ]
    rows = []
    for lock in LOCK_ROWS:
        row = {
            "hunt_code": lock["hunt_code"],
            "hunt_name": lock["hunt_name"],
            "species": lock["species"],
            "sex_type": lock["sex_type"],
            "weapon": lock["weapon"],
            "hunt_type": lock["hunt_type"],
            "season": lock["season"],
            "Non Res": lock["non_res"],
            "Res": lock["res"],
            "Total": lock["total"],
            "permit_status": lock["permit_status"],
            "permit_allocation_type": lock["permit_allocation_type"],
            "permit_source_authority": lock["permit_source_authority"],
            "permit_overlay_source": lock["permit_overlay_source"],
            "data_status": lock["data_status"],
            "model_version": lock["model_version"],
            "rule_version": lock["rule_version"],
            "note": lock["note"],
        }
        rows.append(row)
    write_rows(LOCK_CSV, fieldnames, rows)


def validate_surface(path: Path) -> list[str]:
    _, rows = read_rows(path)
    grouped: dict[str, list[dict[str, str]]] = {code: [] for code in LOCK_CODES}
    for row in rows:
        code = row.get("hunt_code", "").strip()
        if code in grouped:
            grouped[code].append(row)
    errors: list[str] = []
    for code, expected in LOCK_BY_CODE.items():
        matches = grouped[code]
        if not matches:
            errors.append(f"{path}: missing {code}")
            continue
        for row in matches:
            if row.get("permits_2026_total", expected["total"]) != expected["total"]:
                errors.append(f"{path}: {code} permits_2026_total expected {expected['total']!r}")
            if row.get("permit_allotment_2026_total", expected["total"]) != expected["total"]:
                errors.append(f"{path}: {code} permit_allotment_2026_total expected {expected['total']!r}")
            if row.get("public_permits_2026", expected["total"]) != expected["total"]:
                errors.append(f"{path}: {code} public_permits_2026 expected {expected['total']!r}")
            if row.get("quota_2026_total", expected["total"]) != expected["total"]:
                errors.append(f"{path}: {code} quota_2026_total expected {expected['total']!r}")
            if row.get("permit_status", expected["permit_status"]) != expected["permit_status"]:
                errors.append(f"{path}: {code} permit_status expected {expected['permit_status']}")
            if row.get("permit_allotment_2026_status", expected["permit_status"]) != expected["permit_status"]:
                errors.append(f"{path}: {code} permit_allotment_2026_status expected {expected['permit_status']}")
    return errors


def main() -> int:
    write_lock_csv()

    results = [
        update_file(DATABASE, common_updates),
        update_file(HUNT_MASTER, runtime_row_updates),
        update_file(DRAW_REALITY, runtime_row_updates),
        update_file(POINT_LADDER, runtime_row_updates),
        update_file(PREDICTIVE, predictive_updates),
    ]

    runtime_update_rows = [
        update
        for result in results
        for update in result["updates"]
    ]
    write_rows(RUNTIME_UPDATES_CSV, ["file", "hunt_code", "changed", "before", "after"], runtime_update_rows)

    validation_errors = []
    for path in [DATABASE, HUNT_MASTER, DRAW_REALITY, POINT_LADDER, PREDICTIVE]:
        validation_errors.extend(validate_surface(path))

    lock_fieldnames, lock_rows = read_rows(LOCK_CSV)
    duplicate_lock_codes = [
        code
        for code, count in Counter(row["hunt_code"] for row in lock_rows).items()
        if count > 1
    ]
    if duplicate_lock_codes:
        validation_errors.append(f"Duplicate lock rows: {duplicate_lock_codes}")

    summary = {
        "classification": "CONSERVATION_PERMIT_HUNT_CODE_LOCK_2026",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "data_cutoff_date": DATA_CUTOFF_DATE,
        "lock_code_count": len(LOCK_ROWS),
        "lock_codes": [row["hunt_code"] for row in LOCK_ROWS],
        "no_quota_published_codes": [
            row["hunt_code"] for row in LOCK_ROWS if row["permit_status"] == "NO_QUOTA_PUBLISHED"
        ],
        "total_only_codes": [
            row["hunt_code"] for row in LOCK_ROWS if row["permit_status"] == "TOTAL_ONLY"
        ],
        "stale_quota_fixed_codes": ["EA1180"],
        "target_surface_results": {
            str(result["path"].relative_to(ROOT)).replace("\\", "/"): {
                "row_count": result["row_count"],
                "rows_touched": result["touched"],
                "rows_changed": result["changed"],
            }
            for result in results
        },
        "runtime_update_row_count": len(runtime_update_rows),
        "lock_output": str(LOCK_CSV.relative_to(ROOT)).replace("\\", "/"),
        "runtime_updates_output": str(RUNTIME_UPDATES_CSV.relative_to(ROOT)).replace("\\", "/"),
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors,
        "blockers": len(validation_errors),
        "guardrail": "Conservation rows are locked as reference records only; no draw odds, applicant counts, or probability values are invented.",
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Conservation Permit Hunt Code Lock 2026",
        "",
        f"- Lock codes: `{summary['lock_code_count']}`",
        f"- No-quota conservation codes: `{len(summary['no_quota_published_codes'])}`",
        f"- Total-only conservation codes: `{len(summary['total_only_codes'])}`",
        f"- Runtime update rows: `{summary['runtime_update_row_count']}`",
        f"- Blockers: `{summary['blockers']}`",
        "",
        "## Locked Codes",
    ]
    for row in LOCK_ROWS:
        total = row["total"] or "no quota published"
        lines.append(f"- `{row['hunt_code']}` {row['hunt_name']} - {row['permit_status']} - {total}")
    lines.extend(
        [
            "",
            "## Guardrail",
            str(summary["guardrail"]),
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if validation_errors:
        for error in validation_errors:
            print(error)
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
