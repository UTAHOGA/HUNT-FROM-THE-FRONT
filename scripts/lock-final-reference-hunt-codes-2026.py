from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CONSERVATION_CYCLE = ROOT / "data_truth/permit_overlay_truth/normalized/conservation_permit_cycle_rows_2022_2027.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
HUNT_MASTER = ROOT / "processed_data/hunt_master_enriched.csv"
DRAW_REALITY = ROOT / "processed_data/draw_reality_engine.csv"
POINT_LADDER = ROOT / "processed_data/point_ladder_view.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"

LOCK_CSV = ROOT / "data_truth/permit_overlay_truth/normalized/final_reference_hunt_code_lock_2026.csv"
SUMMARY_JSON = ROOT / "processed_data/final_reference_hunt_code_lock_2026_summary.json"
REPORT_MD = ROOT / "processed_data/final_reference_hunt_code_lock_2026.md"
RUNTIME_UPDATES_CSV = ROOT / "processed_data/final_reference_hunt_code_lock_2026_runtime_updates.csv"

DATA_CUTOFF_DATE = "2026-05-25"
CONSERVATION_AUTHORITY = "Utah DWR 2025-2027 Conservation Permit Database"
HUNT_PLANNER_AUTHORITY = "Utah DWR Hunt Planner"
RULE_VERSION = "utah_final_reference_hunt_code_lock_v1.0.0"

NO_QUOTA_NOTE = (
    "Utah DWR source confirms the hunt code and season; no public resident/nonresident quota "
    "or permit total was published for this reference row."
)

LOCK_ROWS: list[dict[str, str]] = [
    {
        "hunt_code": "RS0001",
        "hunt_name": "Rocky Mountain Bighorn Sheep - Statewide Permit",
        "species": "Rocky Mountain Bighorn Sheep",
        "sex_type": "Male Only",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Statewide",
        "season": "Sept 1 - Dec 31, 2026",
        "status": "FULL_SPLIT",
        "source_authority": CONSERVATION_AUTHORITY,
        "source_area": "Statewide",
        "predictive_action": "UPDATE_EXISTING_SPORTSMAN_ROW",
        "model_version": "rocky_bighorn_conservation_reference_v1.0.0",
        "draw_system_type": "SPORTSMAN_PERMIT",
        "draw_pool": "sportsman",
        "display_odds_text": "Sportsman permit draw",
    },
    {
        "hunt_code": "RS1000",
        "hunt_name": "Antelope Island Conservation",
        "species": "Rocky Mountain Bighorn Sheep",
        "sex_type": "Male Only",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Once-in-a-lifetime",
        "season": "Nov 9 2026 - Nov 16 2026",
        "status": "NO_QUOTA_PUBLISHED",
        "source_authority": HUNT_PLANNER_AUTHORITY,
        "source_area": "",
        "predictive_action": "ADD_REFERENCE_ROW",
        "model_version": "rocky_bighorn_reference_v1.0.0",
        "draw_system_type": "ROCKY_BIGHORN_REFERENCE",
        "draw_pool": "rocky_bighorn_reference",
        "display_odds_text": "Rocky Mountain bighorn reference only; odds not modeled",
    },
    {
        "hunt_code": "RS1001",
        "hunt_name": "Book Cliffs, South",
        "species": "Rocky Mountain Bighorn Sheep",
        "sex_type": "Male Only",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Conservation",
        "season": "Nov 1 - Dec 31, 2025",
        "status": "FULL_SPLIT",
        "source_authority": CONSERVATION_AUTHORITY,
        "source_area": "Book Cliffs, South",
        "predictive_action": "ADD_REFERENCE_ROW",
        "model_version": "rocky_bighorn_conservation_reference_v1.0.0",
        "draw_system_type": "CONSERVATION_REFERENCE",
        "draw_pool": "rocky_bighorn_conservation_reference",
        "display_odds_text": "Conservation reference only; odds not modeled",
    },
    {
        "hunt_code": "RS1003",
        "hunt_name": "Box Elder, Newfoundland Mtn",
        "species": "Rocky Mountain Bighorn Sheep",
        "sex_type": "Male Only",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Conservation",
        "season": "Oct 25 - Dec 31, 2025",
        "status": "FULL_SPLIT",
        "source_authority": CONSERVATION_AUTHORITY,
        "source_area": "Box Elder, Newfoundland Mtns (late)",
        "predictive_action": "ADD_REFERENCE_ROW",
        "model_version": "rocky_bighorn_conservation_reference_v1.0.0",
        "draw_system_type": "CONSERVATION_REFERENCE",
        "draw_pool": "rocky_bighorn_conservation_reference",
        "display_odds_text": "Conservation reference only; odds not modeled",
    },
    {
        "hunt_code": "RS1006",
        "hunt_name": "Nine Mile, Gray Canyon",
        "species": "Rocky Mountain Bighorn Sheep",
        "sex_type": "Male Only",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Conservation",
        "season": "Nov 1 - Dec 31, 2025",
        "status": "FULL_SPLIT",
        "source_authority": CONSERVATION_AUTHORITY,
        "source_area": "Nine Mile, Gray Canyon",
        "predictive_action": "ADD_REFERENCE_ROW",
        "model_version": "rocky_bighorn_conservation_reference_v1.0.0",
        "draw_system_type": "CONSERVATION_REFERENCE",
        "draw_pool": "rocky_bighorn_conservation_reference",
        "display_odds_text": "Conservation reference only; odds not modeled",
    },
    {
        "hunt_code": "BI6527",
        "hunt_name": "Nine Mile",
        "species": "Bison",
        "sex_type": "Hunters Choice",
        "weapon": "Any Legal Weapon",
        "hunt_type": "General Season",
        "season": "Aug 1, 2025 - Jan 31, 2026",
        "status": "NO_QUOTA_PUBLISHED",
        "source_authority": HUNT_PLANNER_AUTHORITY,
        "source_area": "",
        "predictive_action": "ADD_REFERENCE_ROW",
        "model_version": "bison_reference_v1.0.0",
        "draw_system_type": "BISON_REFERENCE",
        "draw_pool": "bison_reference",
        "display_odds_text": "Bison reference only; odds not modeled",
    },
    {
        "hunt_code": "BI6538",
        "hunt_name": "Nine Mile, Private Lands Only",
        "species": "Bison",
        "sex_type": "Hunters Choice",
        "weapon": "Any Legal Weapon",
        "hunt_type": "General Season",
        "season": "Aug 1, 2025 - Jan 31, 2026 | Harvest survey due by Feb 15, 2026 Visit: http://wildlife.utah.gov/harvest to submit your survey",
        "status": "NO_QUOTA_PUBLISHED",
        "source_authority": HUNT_PLANNER_AUTHORITY,
        "source_area": "",
        "predictive_action": "ADD_REFERENCE_ROW",
        "model_version": "bison_reference_v1.0.0",
        "draw_system_type": "BISON_REFERENCE",
        "draw_pool": "bison_reference",
        "display_odds_text": "Bison reference only; odds not modeled",
    },
    {
        "hunt_code": "EX1000",
        "hunt_name": "Elk Extended Archery",
        "species": "Elk",
        "sex_type": "Hunters Choice",
        "weapon": "Archery",
        "hunt_type": "Extended Archery",
        "season": "Aug 16 - Dec 15, 2025",
        "status": "NO_QUOTA_PUBLISHED",
        "source_authority": HUNT_PLANNER_AUTHORITY,
        "source_area": "",
        "predictive_action": "ADD_REFERENCE_ROW",
        "model_version": "extended_archery_reference_v1.0.0",
        "draw_system_type": "EXTENDED_ARCHERY_REFERENCE",
        "draw_pool": "extended_archery_reference",
        "display_odds_text": "Extended archery reference only; odds not modeled",
    },
    {
        "hunt_code": "CG9999",
        "hunt_name": "Cougar - Statewide",
        "species": "Cougar",
        "sex_type": "Either Sex",
        "weapon": "Any Legal Weapon",
        "hunt_type": "Statewide",
        "season": "",
        "status": "NO_QUOTA_PUBLISHED",
        "source_authority": HUNT_PLANNER_AUTHORITY,
        "source_area": "",
        "predictive_action": "ADD_REFERENCE_ROW",
        "model_version": "cougar_reference_v1.0.0",
        "draw_system_type": "COUGAR_REFERENCE",
        "draw_pool": "cougar_reference",
        "display_odds_text": "Cougar reference only; odds not modeled",
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
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator=lineterminator)
        writer.writeheader()
        writer.writerows(rows)


def conservation_counts() -> dict[str, dict[str, str]]:
    _, rows = read_rows(CONSERVATION_CYCLE)
    by_area = {
        row["area"]: row
        for row in rows
        if row.get("cycle") == "2025-2027"
        and row.get("species_family") == "Rocky Mountain Bighorn Sheep"
        and row.get("condition_or_weapon") == "Any Legal Weapon"
        and row.get("discontinued_flag") == "False"
    }
    counts: dict[str, dict[str, str]] = {}
    for lock in LOCK_ROWS:
        if lock["status"] != "FULL_SPLIT":
            counts[lock["hunt_code"]] = {"res": "", "nr": "", "total": "", "source_file": "Utah DWR Hunt Planner"}
            continue
        source = by_area.get(lock["source_area"])
        if not source:
            raise RuntimeError(f"Missing Rocky bighorn conservation count for {lock['hunt_code']} {lock['source_area']}")
        total = str(int(float(source["permit_count"])))
        counts[lock["hunt_code"]] = {
            "res": total,
            "nr": "0",
            "total": total,
            "source_file": source.get("source_file", "conservation-permit-hunt-table-2025-27.csv"),
            "source_page_or_row": source.get("source_page_or_row", ""),
            "source_row_id": source.get("source_row_id", ""),
        }
    return counts


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
        "permits_2026_res",
        "permits_2026_nr",
        "permits_2026_total",
        "public_permits_2026",
        "quota_2026_total",
        "permit_allotment_2026_res",
        "permit_allotment_2026_nr",
        "permit_allotment_2026_total",
        "permit_allotment_2026_status",
        "model_version",
        "draw_system_type",
    ]
    return json.dumps({field: row.get(field, "") for field in fields if field in row}, sort_keys=True)


def source_note(lock: dict[str, str], count: dict[str, str]) -> str:
    if lock["status"] == "FULL_SPLIT":
        return (
            f"Permit count {count['total']} pulled from {CONSERVATION_AUTHORITY}; "
            f"source row {count.get('source_page_or_row', '')} for {lock['source_area']}."
        )
    return NO_QUOTA_NOTE


def common_updates(row: dict[str, str], lock: dict[str, str], count: dict[str, str]) -> None:
    total = count["total"]
    status = lock["status"]
    set_if_present(row, "hunt_code", lock["hunt_code"])
    set_if_present(row, "hunt_name", lock["hunt_name"])
    set_if_present(row, "species", lock["species"])
    set_if_present(row, "sex_type", lock["sex_type"])
    set_if_present(row, "weapon", lock["weapon"])
    set_if_present(row, "hunt_type", lock["hunt_type"])
    set_if_present(row, "season", lock["season"])
    set_if_present(row, "season_dates", lock["season"])
    set_if_present(row, "permits_2026_res", count["res"])
    set_if_present(row, "permits_2026_nr", count["nr"])
    set_if_present(row, "permits_2026_total", total)
    set_if_present(row, "public_permits_2026", total)
    set_if_present(row, "quota_2026_total", total)
    set_if_present(row, "permit_allotment_2026_res", count["res"])
    set_if_present(row, "permit_allotment_2026_nr", count["nr"])
    set_if_present(row, "permit_allotment_2026_total", total)
    set_if_present(row, "permit_status", status)
    set_if_present(row, "permit_allocation_type", "FULL_SPLIT" if status == "FULL_SPLIT" else "NO_QUOTA_PUBLISHED")
    set_if_present(row, "permit_source_authority", lock["source_authority"])
    set_if_present(row, "permit_note", source_note(lock, count))
    set_if_present(row, "permit_overlay_source", count["source_file"])
    set_if_present(row, "data_status", "COMPLETE" if status == "FULL_SPLIT" else "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED")
    set_if_present(row, "permit_allotment_2026_status", status)
    set_if_present(row, "permit_allotment_2026_source", lock["source_authority"])
    set_if_present(row, "permit_allotment_2026_source_file", count["source_file"])
    set_if_present(row, "quota_source_status", status)
    set_if_present(row, "quota_source_year", "2026")
    set_if_present(row, "quota_source_file", count["source_file"])
    set_if_present(row, "public_permits_2026_source", lock["source_authority"] if total else "")
    set_if_present(row, "permits_2026_source", lock["source_authority"])
    set_if_present(row, "quota_source", lock["source_authority"])
    set_if_present(row, "permit_source", lock["source_authority"])
    set_if_present(row, "truth_source_file", count["source_file"])
    set_if_present(row, "truth_source_status", "COMPLETE" if status == "FULL_SPLIT" else "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED")
    set_if_present(row, "missing_permits", "FALSE" if status == "FULL_SPLIT" else "TRUE")
    set_if_present(row, "availability_status", "full_split" if status == "FULL_SPLIT" else "no_quota_published")
    set_if_present(row, "data_cutoff_date", DATA_CUTOFF_DATE)
    if lock["hunt_code"] == "BI6538":
        set_if_present(row, "private_land_only_flag", "True")


def predictive_updates(row: dict[str, str], lock: dict[str, str], count: dict[str, str]) -> None:
    common_updates(row, lock, count)
    if lock["hunt_code"] == "RS0001":
        set_if_present(row, "sportsman_permit_count", count["total"])
        return
    status = lock["status"]
    set_if_present(row, "year", "2026")
    set_if_present(row, "forecast_year", "2026")
    set_if_present(row, "hunt_class", lock["hunt_type"])
    set_if_present(row, "residency", "Reference Only")
    set_if_present(row, "points", "0")
    set_if_present(row, "draw_pool", lock["draw_pool"])
    set_if_present(row, "source_years_used", "2026")
    set_if_present(row, "source_year_count", "1")
    set_if_present(row, "latest_source_year", "2026")
    set_if_present(row, "earliest_source_year", "2026")
    set_if_present(row, "source_dataset", "2026_final_reference_hunt_code_lock")
    set_if_present(row, "model_strategy", lock["draw_system_type"])
    set_if_present(row, "draw_system_type", lock["draw_system_type"])
    set_if_present(row, "algorithm_status", lock["draw_system_type"])
    set_if_present(row, "target_scope", "TARGET")
    set_if_present(row, "modeled_by_engine", "False")
    set_if_present(row, "reason", f"{source_note(lock, count)} No draw odds or probability value was invented.")
    set_if_present(row, "model_version", lock["model_version"])
    set_if_present(row, "rule_version", RULE_VERSION)
    set_if_present(row, "reason_codes", f"FINAL_REFERENCE_CODE_LOCK|{status}|NO_DRAW_PROBABILITY_INVENTED")
    set_if_present(row, "status", "reference_no_draw_odds")
    set_if_present(row, "trend", "not_modeled")
    set_if_present(row, "permit_availability_type", lock["draw_pool"])
    set_if_present(row, "probability_model", "NONE")
    set_if_present(row, "rule_status", "reference_only")
    set_if_present(row, "data_quality_flags", f"FINAL_REFERENCE_CODE_LOCK;NO_DRAW_PROBABILITY_MODELED;{status}")
    set_if_present(row, "prediction_year", "2026")
    set_if_present(row, "source_year", "2026")
    set_if_present(row, "applicant_forecast_method", "not_modeled_reference")
    set_if_present(row, "display_odds_text", lock["display_odds_text"])
    set_if_present(row, "data_quality_grade", "A")


def predictive_reference_row(fieldnames: list[str], lock: dict[str, str], count: dict[str, str]) -> dict[str, str]:
    row = {field: "" for field in fieldnames}
    predictive_updates(row, lock, count)
    return row


def update_file(path: Path, counts: dict[str, dict[str, str]]) -> dict[str, object]:
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
        common_updates(row, LOCK_BY_CODE[code], counts[code])
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
    write_rows(path, fieldnames, rows, lineterminator="\n" if path == DATABASE else "\r\n")
    return {"path": path, "row_count": len(rows), "touched": touched, "changed": changed, "updates": updates}


def promote_predictive_rows(counts: dict[str, dict[str, str]]) -> dict[str, object]:
    fieldnames, rows = read_rows(PREDICTIVE)
    existing = {row.get("hunt_code", "").strip() for row in rows}
    added: list[str] = []
    for code in sorted(ADD_PREDICTIVE_CODES):
        if code in existing:
            continue
        rows.append(predictive_reference_row(fieldnames, LOCK_BY_CODE[code], counts[code]))
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
        predictive_updates(row, LOCK_BY_CODE[code], counts[code])
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


def write_lock_csv(counts: dict[str, dict[str, str]]) -> None:
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
    rows = []
    for lock in LOCK_ROWS:
        count = counts[lock["hunt_code"]]
        rows.append(
            {
                "Hunt Name": lock["hunt_name"],
                "Hunt Code": lock["hunt_code"],
                "Sex": lock["sex_type"],
                "Species": lock["species"],
                "Weapon": lock["weapon"],
                "Hunt Type": lock["hunt_type"],
                "Season": lock["season"],
                "Non Res": count["nr"],
                "Res": count["res"],
                "Total": count["total"],
                "Permit Status": lock["status"],
                "Source Authority": lock["source_authority"],
                "Source File": count["source_file"],
                "Data Status": "COMPLETE" if lock["status"] == "FULL_SPLIT" else "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED",
                "Note": source_note(lock, count),
            }
        )
    write_rows(LOCK_CSV, fieldnames, rows)


def write_runtime_updates(results: list[dict[str, object]], predictive_result: dict[str, object]) -> None:
    rows: list[dict[str, str]] = []
    for result in [*results, predictive_result]:
        rows.extend(result["updates"])  # type: ignore[arg-type]
    write_rows(RUNTIME_UPDATES_CSV, ["file", "hunt_code", "changed", "before", "after"], rows)


def validate_surface(path: Path, counts: dict[str, dict[str, str]], predictive: bool = False) -> dict[str, object]:
    _, rows = read_rows(path)
    rows_by_code: dict[str, list[dict[str, str]]] = {code: [] for code in LOCK_CODES}
    for row in rows:
        code = row.get("hunt_code", "").strip()
        if code in rows_by_code:
            rows_by_code[code].append(row)

    missing = sorted(code for code, code_rows in rows_by_code.items() if not code_rows)
    quota_mismatches: list[dict[str, str]] = []
    bad_predictive: list[dict[str, str]] = []
    for code, code_rows in rows_by_code.items():
        lock = LOCK_BY_CODE[code]
        count = counts[code]
        for row in code_rows:
            for field, expected in (
                ("permits_2026_res", count["res"]),
                ("permits_2026_nr", count["nr"]),
                ("permits_2026_total", count["total"]),
                ("permit_allotment_2026_total", count["total"]),
            ):
                if field not in row:
                    continue
                if row.get(field, "") != expected:
                    quota_mismatches.append({"hunt_code": code, "field": field, "expected": expected, "actual": row.get(field, "")})
            if row.get("permit_allotment_2026_status", lock["status"]) != lock["status"]:
                quota_mismatches.append(
                    {
                        "hunt_code": code,
                        "field": "permit_allotment_2026_status",
                        "expected": lock["status"],
                        "actual": row.get("permit_allotment_2026_status", ""),
                    }
                )
            if predictive and code != "RS0001":
                if row.get("modeled_by_engine") != "False" or row.get("probability_model") != "NONE":
                    bad_predictive.append({"hunt_code": code, "reason": "modeled_or_probability_not_disabled"})
                if row.get("draw_system_type") != lock["draw_system_type"]:
                    bad_predictive.append({"hunt_code": code, "reason": "wrong_draw_system_type"})
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "missing_codes": missing,
        "quota_mismatch_count": len(quota_mismatches),
        "quota_mismatches": quota_mismatches[:20],
        "bad_predictive_row_count": len(bad_predictive),
        "bad_predictive_rows": bad_predictive[:20],
        "rows_by_code_counts": {code: len(rows_by_code[code]) for code in sorted(LOCK_CODES)},
    }


def build_summary(
    counts: dict[str, dict[str, str]], results: list[dict[str, object]], predictive_result: dict[str, object]
) -> dict[str, object]:
    validations = [
        validate_surface(DATABASE, counts),
        validate_surface(HUNT_MASTER, counts),
        validate_surface(DRAW_REALITY, counts),
        validate_surface(POINT_LADDER, counts),
        validate_surface(PREDICTIVE, counts, predictive=True),
    ]
    blockers = []
    for validation in validations:
        if validation["missing_codes"]:
            blockers.append({"path": validation["path"], "reason": "missing_codes", "codes": validation["missing_codes"]})
        if validation["quota_mismatch_count"]:
            blockers.append(
                {"path": validation["path"], "reason": "quota_mismatches", "examples": validation["quota_mismatches"]}
            )
        if validation["bad_predictive_row_count"]:
            blockers.append(
                {"path": validation["path"], "reason": "bad_predictive_rows", "examples": validation["bad_predictive_rows"]}
            )
    return {
        "classification": "FINAL_REFERENCE_HUNT_CODE_LOCK_2026",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_cutoff_date": DATA_CUTOFF_DATE,
        "rule_version": RULE_VERSION,
        "lock_code_count": len(LOCK_CODES),
        "lock_codes": sorted(LOCK_CODES),
        "predictive_reference_codes_locked": sorted(ADD_PREDICTIVE_CODES),
        "predictive_reference_codes_added_this_run": predictive_result["predictive_reference_codes_added_this_run"],
        "permit_status_counts": dict(Counter(row["status"] for row in LOCK_ROWS)),
        "counts_by_code": counts,
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
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# Final Reference Hunt Code Lock 2026",
                "",
                f"- Locked codes: {summary['lock_code_count']}",
                f"- Predictive rows added: {len(summary['predictive_reference_codes_added_this_run'])}",
                f"- Blockers: {summary['blocker_count']}",
                "",
                "The remaining current-database predictive gaps were promoted as traceable reference rows without inventing draw odds.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    counts = conservation_counts()
    write_lock_csv(counts)
    results = [update_file(path, counts) for path in [DATABASE, HUNT_MASTER, DRAW_REALITY, POINT_LADDER]]
    predictive_result = promote_predictive_rows(counts)
    write_runtime_updates(results, predictive_result)
    summary = build_summary(counts, results, predictive_result)
    write_summary(summary)
    if summary["blocker_count"]:
        raise SystemExit(f"Final reference hunt code lock failed validation: {summary['blockers']}")


if __name__ == "__main__":
    main()
