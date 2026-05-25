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

LOCK_CSV = ROOT / "data_truth/permit_overlay_truth/normalized/private_land_deer_hunt_code_lock_2026.csv"
SUMMARY_JSON = ROOT / "processed_data/private_land_deer_hunt_code_lock_2026_summary.json"
REPORT_MD = ROOT / "processed_data/private_land_deer_hunt_code_lock_2026.md"
RUNTIME_UPDATES_CSV = ROOT / "processed_data/private_land_deer_hunt_code_lock_2026_runtime_updates.csv"

DATA_CUTOFF_DATE = "2026-05-25"
SOURCE_AUTHORITY = "Utah DWR Hunt Planner"
SOURCE_FILE = "2026_deer_buck_limited_entry_private_lands_only.csv"
RULE_VERSION = "utah_private_land_deer_code_lock_v1.0.0"
MODEL_VERSION = "private_land_deer_reference_v1.0.0"

NO_QUOTA_NOTE = (
    "Utah DWR Hunt Planner source confirms private-land limited-entry deer hunt; "
    "no public resident/nonresident quota or permit total is published for this reference row."
)

LOCK_ROWS: list[dict[str, str]] = [
    {
        "hunt_code": "LD1001",
        "hunt_name": "Paunsaugunt - Private Land Only",
        "boundary_id": "163",
        "sex_type": "Buck",
        "weapon": "Archery",
        "season": "Aug 16 2025 - Sept 12 2025 - Private Land Only",
        "predictive_action": "ADD_REFERENCE_ROW",
    },
    {
        "hunt_code": "LD1004",
        "hunt_name": "Paunsaugunt - Private Land Only",
        "boundary_id": "163",
        "sex_type": "Buck",
        "weapon": "Any Legal Weapon",
        "season": "Oct 18 2025 - Oct 31 2025 - Private Land Only",
        "predictive_action": "ADD_REFERENCE_ROW",
    },
    {
        "hunt_code": "LD1006",
        "hunt_name": "Paunsaugunt - Private Land Only",
        "boundary_id": "163",
        "sex_type": "Buck",
        "weapon": "Muzzleloader",
        "season": "Sept 24 2025 - Oct 02 2025 - Private Land Only",
        "predictive_action": "ADD_REFERENCE_ROW",
    },
    {
        "hunt_code": "LD1019",
        "hunt_name": "Fillmore, Oak Creek LE - Private Land Only",
        "boundary_id": "85",
        "sex_type": "Buck",
        "weapon": "Any Legal Weapon",
        "season": "Oct 18 2025 - Oct 26 2025 - Private Land Only",
        "predictive_action": "ADD_REFERENCE_ROW",
    },
    {
        "hunt_code": "LD1023",
        "hunt_name": "Diamond Mtn - Private Land Only",
        "boundary_id": "206",
        "sex_type": "Buck",
        "weapon": "Any Legal Weapon",
        "season": "Oct 18 2025 - Oct 26 2025 - Private Land Only",
        "predictive_action": "ADD_REFERENCE_ROW",
    },
    {
        "hunt_code": "LD1108",
        "hunt_name": "Thousand Lakes - Private Land Only",
        "boundary_id": "632",
        "sex_type": "Buck",
        "weapon": "Restricted Rifle",
        "season": "Oct 18 2025 - Oct 26 2025 - Private Land Only",
        "predictive_action": "ADD_REFERENCE_ROW",
    },
    {
        "hunt_code": "LO0008",
        "hunt_name": "Diamond Mtn Landowner Association",
        "boundary_id": "206",
        "sex_type": "Buck",
        "weapon": "Archery",
        "season": "Aug 15 2026 - Sept 11 2026 - Valid only on property enrolled in the Diamond Mtn LOA",
        "predictive_action": "UPDATE_EXISTING_REFERENCE",
    },
    {
        "hunt_code": "LO0009",
        "hunt_name": "Diamond Mtn Landowner Association",
        "boundary_id": "206",
        "sex_type": "Buck",
        "weapon": "Any Legal Weapon",
        "season": "Oct 17 2026 - Oct 25 2026 - Valid only on property enrolled in the Diamond Mtn LOA",
        "predictive_action": "UPDATE_EXISTING_REFERENCE",
    },
    {
        "hunt_code": "LO0010",
        "hunt_name": "Diamond Mtn Landowner Association",
        "boundary_id": "206",
        "sex_type": "Buck",
        "weapon": "Muzzleloader",
        "season": "Sept 23 2026 - Oct 01 2026 - Valid only on property enrolled in the Diamond Mtn LOA",
        "predictive_action": "UPDATE_EXISTING_REFERENCE",
    },
]

LOCK_BY_CODE = {row["hunt_code"]: row for row in LOCK_ROWS}
LOCK_CODES = set(LOCK_BY_CODE)
ADD_PREDICTIVE_CODES = {row["hunt_code"] for row in LOCK_ROWS if row["predictive_action"] == "ADD_REFERENCE_ROW"}


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
        "permit_allotment_2026_res",
        "permit_allotment_2026_nr",
        "permit_allotment_2026_total",
        "permit_status",
        "permit_allotment_2026_status",
        "data_status",
        "model_version",
        "draw_pool",
        "draw_system_type",
    ]
    return json.dumps({field: row.get(field, "") for field in fields if field in row}, sort_keys=True)


def common_updates(row: dict[str, str], lock: dict[str, str]) -> None:
    set_if_present(row, "hunt_code", lock["hunt_code"])
    set_if_present(row, "boundary_id", lock["boundary_id"])
    set_if_present(row, "hunt_name", lock["hunt_name"])
    set_if_present(row, "species", "Deer")
    set_if_present(row, "sex_type", lock["sex_type"])
    set_if_present(row, "weapon", lock["weapon"])
    set_if_present(row, "hunt_type", "Limited Entry - Private Land Only")
    set_if_present(row, "access_type", "Private Land Only")
    set_if_present(row, "season", lock["season"])
    set_if_present(row, "season_dates", lock["season"])

    for field in (
        "permits_2026_res",
        "permits_2026_nr",
        "permits_2026_total",
        "public_permits_2026",
        "quota_2026_total",
        "quota_2026_max_pool",
        "quota_2026_random_pool",
        "permit_allotment_2026_res",
        "permit_allotment_2026_nr",
        "permit_allotment_2026_total",
    ):
        set_if_present(row, field, "")

    set_if_present(row, "permits_2026_source", SOURCE_AUTHORITY)
    set_if_present(row, "public_permits_2026_source", "")
    set_if_present(row, "permit_status", "NO_QUOTA_PUBLISHED")
    set_if_present(row, "permit_allocation_type", "NO_QUOTA_PUBLISHED")
    set_if_present(row, "permit_source_authority", SOURCE_AUTHORITY)
    set_if_present(row, "permit_note", NO_QUOTA_NOTE)
    set_if_present(row, "permit_overlay_source", SOURCE_FILE)
    set_if_present(row, "data_status", "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED")
    set_if_present(row, "permit_allotment_2026_status", "NO_QUOTA_PUBLISHED")
    set_if_present(row, "permit_allotment_2026_source", SOURCE_AUTHORITY)
    set_if_present(row, "permit_allotment_2026_source_file", SOURCE_FILE)
    set_if_present(row, "quota_source_status", "NO_QUOTA_PUBLISHED")
    set_if_present(row, "quota_source_year", "2026")
    set_if_present(row, "quota_source_file", SOURCE_FILE)
    set_if_present(row, "quota_source", SOURCE_AUTHORITY)
    set_if_present(row, "permit_source", SOURCE_AUTHORITY)
    set_if_present(row, "truth_source_file", SOURCE_FILE)
    set_if_present(row, "truth_source_status", "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED")
    set_if_present(row, "missing_permits", "TRUE")
    set_if_present(row, "availability_status", "no_quota_published")
    set_if_present(row, "data_cutoff_date", DATA_CUTOFF_DATE)
    set_if_present(row, "private_land_only_flag", "True")


def predictive_updates(row: dict[str, str], lock: dict[str, str]) -> None:
    common_updates(row, lock)
    set_if_present(row, "year", "2026")
    set_if_present(row, "forecast_year", "2026")
    set_if_present(row, "hunt_class", "Private Land Deer Reference")
    set_if_present(row, "residency", "Private Land Only")
    set_if_present(row, "points", "0")
    set_if_present(row, "draw_pool", "private_land_deer_reference")
    set_if_present(row, "source_years_used", "2026")
    set_if_present(row, "source_year_count", "1")
    set_if_present(row, "latest_source_year", "2026")
    set_if_present(row, "earliest_source_year", "2026")
    set_if_present(row, "source_dataset", "2026_private_land_deer_hunt_code_lock")
    set_if_present(row, "model_strategy", "PRIVATE_LAND_DEER_REFERENCE")
    set_if_present(row, "draw_system_type", "PRIVATE_LAND_DEER_REFERENCE")
    set_if_present(row, "algorithm_status", "PRIVATE_LAND_DEER_REFERENCE")
    set_if_present(row, "target_scope", "TARGET")
    set_if_present(row, "modeled_by_engine", "False")
    set_if_present(row, "reason", f"{NO_QUOTA_NOTE} No draw odds or probability value was invented.")
    if not row.get("model_version"):
        set_if_present(row, "model_version", MODEL_VERSION)
    set_if_present(row, "rule_version", RULE_VERSION)
    set_if_present(row, "reason_codes", "PRIVATE_LAND_DEER_CODE_LOCK|NO_QUOTA_PUBLISHED|NO_DRAW_PROBABILITY_INVENTED")
    set_if_present(row, "status", "private_land_deer_reference_no_draw_odds")
    set_if_present(row, "trend", "not_modeled")
    set_if_present(row, "permit_availability_type", "private_land_deer_reference")
    set_if_present(row, "probability_model", "NONE")
    set_if_present(row, "rule_status", "private_land_deer_reference")
    set_if_present(row, "data_quality_flags", "PRIVATE_LAND_DEER_CODE_LOCK;NO_DRAW_PROBABILITY_MODELED;NO_QUOTA_PUBLISHED")
    set_if_present(row, "prediction_year", "2026")
    set_if_present(row, "source_year", "2026")
    set_if_present(row, "applicant_forecast_method", "not_modeled_private_land_deer_reference")
    set_if_present(row, "display_odds_text", "Private-land deer reference only; odds not modeled")
    set_if_present(row, "data_quality_grade", "A")


def predictive_reference_row(fieldnames: list[str], lock: dict[str, str]) -> dict[str, str]:
    row = {field: "" for field in fieldnames}
    row["model_version"] = MODEL_VERSION
    predictive_updates(row, lock)
    return row


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


def promote_predictive_rows() -> dict[str, object]:
    fieldnames, rows = read_rows(PREDICTIVE)
    existing = {row.get("hunt_code", "").strip() for row in rows}
    added: list[str] = []
    for code in sorted(ADD_PREDICTIVE_CODES):
        if code in existing:
            continue
        rows.append(predictive_reference_row(fieldnames, LOCK_BY_CODE[code]))
        added.append(code)

    touched = 0
    changed = 0
    updates: list[dict[str, str]] = []
    for row in rows:
        code = row.get("hunt_code", "").strip()
        if code not in LOCK_BY_CODE:
            continue
        touched += 1
        before = snapshot(row)
        predictive_updates(row, LOCK_BY_CODE[code])
        after = snapshot(row)
        if before != after:
            changed += 1
        updates.append(
            {
                "file": str(PREDICTIVE.relative_to(ROOT)).replace("\\", "/"),
                "hunt_code": code,
                "changed": "TRUE" if before != after else "FALSE",
                "before": before,
                "after": after,
            }
        )

    write_rows(PREDICTIVE, fieldnames, rows, lineterminator="\r\n")
    return {
        "path": PREDICTIVE,
        "row_count": len(rows),
        "touched": touched,
        "changed": changed,
        "predictive_reference_codes_added_this_run": added,
        "updates": updates,
    }


def write_lock_csv() -> None:
    fieldnames = [
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
        "Permit Status",
        "Source Authority",
        "Source File",
        "Data Status",
        "Note",
    ]
    rows = [
        {
            "Hunt Name": lock["hunt_name"],
            "Hunt Code": lock["hunt_code"],
            "Sex": lock["sex_type"],
            "Species": "Deer",
            "Weapon": lock["weapon"],
            "Hunt Type": "Limited Entry - Private Land Only",
            "Season": lock["season"],
            "Non Res": "",
            "Res": "",
            "Total": "",
            "Permit Status": "NO_QUOTA_PUBLISHED",
            "Source Authority": SOURCE_AUTHORITY,
            "Source File": SOURCE_FILE,
            "Data Status": "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED",
            "Note": NO_QUOTA_NOTE,
        }
        for lock in LOCK_ROWS
    ]
    write_rows(LOCK_CSV, fieldnames, rows)


def write_runtime_updates(results: list[dict[str, object]], predictive_result: dict[str, object]) -> None:
    rows: list[dict[str, str]] = []
    for result in [*results, predictive_result]:
        rows.extend(result["updates"])  # type: ignore[arg-type]
    write_rows(RUNTIME_UPDATES_CSV, ["file", "hunt_code", "changed", "before", "after"], rows)


def validate_surface(path: Path, expected_codes: set[str], predictive: bool = False) -> dict[str, object]:
    _, rows = read_rows(path)
    rows_by_code: dict[str, list[dict[str, str]]] = {code: [] for code in expected_codes}
    for row in rows:
        code = row.get("hunt_code", "").strip()
        if code in expected_codes:
            rows_by_code[code].append(row)

    missing = sorted(code for code, code_rows in rows_by_code.items() if not code_rows)
    quota_leaks: list[dict[str, str]] = []
    bad_statuses: list[dict[str, str]] = []
    bad_predictive_rows: list[dict[str, str]] = []
    for code, code_rows in rows_by_code.items():
        for row in code_rows:
            for field in (
                "permits_2026_res",
                "permits_2026_nr",
                "permits_2026_total",
                "public_permits_2026",
                "quota_2026_total",
                "permit_allotment_2026_res",
                "permit_allotment_2026_nr",
                "permit_allotment_2026_total",
            ):
                if row.get(field, "").strip():
                    quota_leaks.append({"hunt_code": code, "field": field, "value": row[field]})
            status = row.get("permit_allotment_2026_status") or row.get("permit_status")
            if status and status != "NO_QUOTA_PUBLISHED":
                bad_statuses.append({"hunt_code": code, "status": status})
            if predictive:
                if row.get("modeled_by_engine") != "False" or row.get("probability_model") != "NONE":
                    bad_predictive_rows.append({"hunt_code": code, "reason": "modeled_or_probability_not_disabled"})
                if row.get("draw_system_type") != "PRIVATE_LAND_DEER_REFERENCE":
                    bad_predictive_rows.append({"hunt_code": code, "reason": "wrong_draw_system_type"})
                if row.get("residency") != "Private Land Only":
                    bad_predictive_rows.append({"hunt_code": code, "reason": "wrong_residency"})
                if row.get("private_land_only_flag") != "True":
                    bad_predictive_rows.append({"hunt_code": code, "reason": "private_land_flag_missing"})
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "missing_codes": missing,
        "quota_leak_count": len(quota_leaks),
        "quota_leaks": quota_leaks[:20],
        "bad_status_count": len(bad_statuses),
        "bad_statuses": bad_statuses[:20],
        "bad_predictive_row_count": len(bad_predictive_rows),
        "bad_predictive_rows": bad_predictive_rows[:20],
        "rows_by_code_counts": {code: len(rows_by_code[code]) for code in sorted(expected_codes)},
    }


def build_summary(results: list[dict[str, object]], predictive_result: dict[str, object]) -> dict[str, object]:
    validations = [
        validate_surface(DATABASE, LOCK_CODES),
        validate_surface(HUNT_MASTER, LOCK_CODES),
        validate_surface(DRAW_REALITY, LOCK_CODES),
        validate_surface(POINT_LADDER, LOCK_CODES),
        validate_surface(PREDICTIVE, LOCK_CODES, predictive=True),
    ]
    blockers = []
    for validation in validations:
        if validation["missing_codes"]:
            blockers.append({"path": validation["path"], "reason": "missing_codes", "codes": validation["missing_codes"]})
        if validation["quota_leak_count"]:
            blockers.append({"path": validation["path"], "reason": "quota_leaks", "examples": validation["quota_leaks"]})
        if validation["bad_status_count"]:
            blockers.append({"path": validation["path"], "reason": "bad_statuses", "examples": validation["bad_statuses"]})
        if validation["bad_predictive_row_count"]:
            blockers.append(
                {"path": validation["path"], "reason": "bad_predictive_rows", "examples": validation["bad_predictive_rows"]}
            )

    lock_status_counts = Counter("NO_QUOTA_PUBLISHED" for _ in LOCK_ROWS)
    return {
        "classification": "PRIVATE_LAND_DEER_HUNT_CODE_LOCK_2026",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_cutoff_date": DATA_CUTOFF_DATE,
        "source_authority": SOURCE_AUTHORITY,
        "source_file": SOURCE_FILE,
        "rule_version": RULE_VERSION,
        "model_version_for_new_ld_rows": MODEL_VERSION,
        "locked_hunt_code_count": len(LOCK_CODES),
        "locked_hunt_codes": sorted(LOCK_CODES),
        "ld_predictive_reference_codes_added_this_run": predictive_result["predictive_reference_codes_added_this_run"],
        "existing_lo_reference_codes_checked": sorted(LOCK_CODES - ADD_PREDICTIVE_CODES),
        "permit_status_counts": dict(lock_status_counts),
        "runtime_update_counts": {
            str(result["path"].relative_to(ROOT)).replace("\\", "/"): {
                "touched": result["touched"],
                "changed": result["changed"],
            }
            for result in [*results, predictive_result]
        },
        "surface_validations": validations,
        "blocker_count": len(blockers),
        "blockers": blockers,
    }


def write_summary(summary: dict[str, object]) -> None:
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# Private-Land Deer Hunt Code Lock 2026",
                "",
                f"- Locked hunt codes: {summary['locked_hunt_code_count']}",
                f"- LD predictive rows added: {len(summary['ld_predictive_reference_codes_added_this_run'])}",
                "- Permit status: NO_QUOTA_PUBLISHED for all locked rows",
                f"- Blockers: {summary['blocker_count']}",
                "",
                "These rows are reference-only private-land deer hunts. No public quota, resident split, nonresident split, or draw probability was invented.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    write_lock_csv()
    results = [
        update_file(DATABASE, common_updates),
        update_file(HUNT_MASTER, common_updates),
        update_file(DRAW_REALITY, common_updates),
        update_file(POINT_LADDER, common_updates),
    ]
    predictive_result = promote_predictive_rows()
    write_runtime_updates(results, predictive_result)
    summary = build_summary(results, predictive_result)
    write_summary(summary)
    if summary["blocker_count"]:
        raise SystemExit(f"Private-land deer hunt code lock failed validation: {summary['blockers']}")


if __name__ == "__main__":
    main()
