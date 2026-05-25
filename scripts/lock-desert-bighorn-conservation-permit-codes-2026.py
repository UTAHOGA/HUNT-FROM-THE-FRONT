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

LOCK_CSV = ROOT / "data_truth/permit_overlay_truth/normalized/desert_bighorn_conservation_permit_code_lock_2026.csv"
SUMMARY_JSON = ROOT / "processed_data/desert_bighorn_conservation_permit_code_lock_2026_summary.json"
REPORT_MD = ROOT / "processed_data/desert_bighorn_conservation_permit_code_lock_2026.md"
RUNTIME_UPDATES_CSV = ROOT / "processed_data/desert_bighorn_conservation_permit_code_lock_2026_runtime_updates.csv"

DATA_CUTOFF_DATE = "2026-05-25"
SOURCE_FILE = "conservation-permit-hunt-table-2025-27.csv"
SOURCE_AUTHORITY = "Utah DWR 2025-2027 Conservation Permit Database"
RULE_VERSION = "utah_desert_bighorn_conservation_code_lock_v1.0.0"
MODEL_VERSION = "desert_bighorn_conservation_reference_v1.0.0"

TARGETS = [
    {
        "hunt_code": "DS1000",
        "hunt_name": "Desert Bighorn Sheep - Statewide Permit",
        "area": "Statewide",
        "sex_type": "Male Only",
        "predictive_action": "UPDATE_EXISTING_SPORTSMAN_ROW",
        "season": "Sept 1 - Dec 31, 2026",
        "hunt_type": "Statewide",
    },
    {
        "hunt_code": "DS1002",
        "hunt_name": "Kaiparowits, East",
        "area": "Kaiparowits, East",
        "sex_type": "Male Only",
        "predictive_action": "ADD_REFERENCE_ROW",
        "season": "Sept 13, 2025 - Dec 31, 2025",
        "hunt_type": "Conservation",
    },
    {
        "hunt_code": "DS1003",
        "hunt_name": "Kaiparowits, Escalante East/West",
        "area": "Kaiparowits, Escalante",
        "sex_type": "Male Only",
        "predictive_action": "ADD_REFERENCE_ROW",
        "season": "Sept 12 - Nov 10, 2026",
        "hunt_type": "Conservation",
    },
    {
        "hunt_code": "DS1004",
        "hunt_name": "San Rafael, Dirty Devil",
        "area": "San Rafael, Dirty Devil",
        "sex_type": "Male Only",
        "predictive_action": "ADD_REFERENCE_ROW",
        "season": "Sept 13 - Dec 31, 2025",
        "hunt_type": "Conservation",
    },
    {
        "hunt_code": "DS1006",
        "hunt_name": "Kaiparowits, West",
        "area": "Kaiparowits, West",
        "sex_type": "Male Only",
        "predictive_action": "ADD_REFERENCE_ROW",
        "season": "Sept 13, 2025 - Dec 31, 2025",
        "hunt_type": "Conservation",
    },
    {
        "hunt_code": "DS1007",
        "hunt_name": "San Rafael, South",
        "area": "San Rafael, South",
        "sex_type": "Male Only",
        "predictive_action": "ADD_REFERENCE_ROW",
        "season": "Sept 13, 2025 - Dec 31, 2025",
        "hunt_type": "Conservation",
    },
    {
        "hunt_code": "DS6605",
        "hunt_name": "Pine Valley, Beaver Dam",
        "area": "Pine Valley, Beaver Dam",
        "sex_type": "Male Only",
        "predictive_action": "ADD_REFERENCE_ROW",
        "season": "Sept 13, 2025 - Dec 31, 2025",
        "hunt_type": "Conservation",
    },
]

TARGET_BY_CODE = {row["hunt_code"]: row for row in TARGETS}
TARGET_CODES = set(TARGET_BY_CODE)
MISSING_PREDICTIVE_CODES = {
    row["hunt_code"] for row in TARGETS if row["predictive_action"] == "ADD_REFERENCE_ROW"
}


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


def clean_int(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    number = float(text)
    if not number.is_integer():
        raise ValueError(f"Expected integer permit count, got {value!r}")
    return str(int(number))


def conservation_counts() -> dict[str, dict[str, str]]:
    _, rows = read_rows(CONSERVATION_CYCLE)
    by_area = {
        row.get("area", ""): row
        for row in rows
        if row.get("cycle") == "2025-2027"
        and row.get("species_family") == "Desert Bighorn Sheep"
        and row.get("condition_or_weapon") == "Any Legal Weapon"
        and row.get("discontinued_flag") == "False"
    }
    counts: dict[str, dict[str, str]] = {}
    for target in TARGETS:
        source = by_area.get(target["area"])
        if not source:
            raise RuntimeError(f"Missing conservation permit source count for {target['hunt_code']} {target['area']}")
        counts[target["hunt_code"]] = {
            "total": clean_int(source["permit_count"]),
            "source_row_id": source.get("source_row_id", ""),
            "source_page_or_row": source.get("source_page_or_row", ""),
            "organization": source.get("organization", ""),
            "group": source.get("group", ""),
            "source_file": source.get("source_file", SOURCE_FILE),
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
    ]
    return json.dumps({field: row.get(field, "") for field in fields if field in row}, sort_keys=True)


def source_note(target: dict[str, str], count: dict[str, str]) -> str:
    return (
        f"Conservation permit count {count['total']} pulled from {SOURCE_AUTHORITY}; "
        f"source row {count['source_page_or_row']} for {target['area']}."
    )


def common_updates(row: dict[str, str], target: dict[str, str], count: dict[str, str]) -> None:
    total = count["total"]
    set_if_present(row, "hunt_name", target["hunt_name"])
    set_if_present(row, "species", "Desert Bighorn Sheep")
    set_if_present(row, "sex_type", target["sex_type"])
    set_if_present(row, "weapon", "Any Legal Weapon")
    set_if_present(row, "hunt_type", target["hunt_type"])
    set_if_present(row, "season", target["season"])
    set_if_present(row, "season_dates", target["season"])
    set_if_present(row, "permits_2026_res", total)
    set_if_present(row, "permits_2026_nr", "0")
    set_if_present(row, "permits_2026_total", total)
    set_if_present(row, "public_permits_2026", total)
    set_if_present(row, "quota_2026_total", total)
    set_if_present(row, "permit_allotment_2026_res", total)
    set_if_present(row, "permit_allotment_2026_nr", "0")
    set_if_present(row, "permit_allotment_2026_total", total)
    set_if_present(row, "permit_status", "FULL_SPLIT")
    set_if_present(row, "permit_allocation_type", "CONSERVATION_PERMIT_FULL_SPLIT")
    set_if_present(row, "permit_source_authority", SOURCE_AUTHORITY)
    set_if_present(row, "permit_note", source_note(target, count))
    set_if_present(row, "permit_overlay_source", count["source_file"])
    set_if_present(row, "data_status", "COMPLETE")
    set_if_present(row, "permit_allotment_2026_status", "FULL_SPLIT")
    set_if_present(row, "permit_allotment_2026_source", SOURCE_AUTHORITY)
    set_if_present(row, "permit_allotment_2026_source_file", count["source_file"])
    set_if_present(row, "quota_source_status", "FULL_SPLIT")
    set_if_present(row, "quota_source_file", count["source_file"])
    set_if_present(row, "quota_source_year", "2026")
    set_if_present(row, "public_permits_2026_source", SOURCE_AUTHORITY)
    set_if_present(row, "permits_2026_source", SOURCE_AUTHORITY)
    set_if_present(row, "quota_source", SOURCE_AUTHORITY)
    set_if_present(row, "permit_source", SOURCE_AUTHORITY)
    set_if_present(row, "truth_source_file", count["source_file"])
    set_if_present(row, "truth_source_status", "COMPLETE")
    set_if_present(row, "missing_permits", "FALSE")
    set_if_present(row, "availability_status", "full_split")
    set_if_present(row, "data_cutoff_date", DATA_CUTOFF_DATE)


def predictive_reference_row(fieldnames: list[str], target: dict[str, str], count: dict[str, str]) -> dict[str, str]:
    row = {field: "" for field in fieldnames}
    row.update(
        {
            "year": "2026",
            "forecast_year": "2026",
            "hunt_code": target["hunt_code"],
            "hunt_name": target["hunt_name"],
            "species": "Desert Bighorn Sheep",
            "sex_type": target["sex_type"],
            "hunt_type": target["hunt_type"],
            "hunt_class": "Conservation",
            "residency": "Reference Only",
            "points": "0",
            "draw_pool": "desert_bighorn_conservation_reference",
            "source_years_used": "2026",
            "source_year_count": "1",
            "latest_source_year": "2026",
            "earliest_source_year": "2026",
            "source_dataset": "2026_desert_bighorn_conservation_permit_code_lock",
            "model_strategy": "DESERT_BIGHORN_CONSERVATION_REFERENCE",
            "draw_system_type": "CONSERVATION_REFERENCE",
            "season_dates": target["season"],
            "weapon": "Any Legal Weapon",
            "algorithm_status": "CONSERVATION_REFERENCE",
            "target_scope": "TARGET",
            "modeled_by_engine": "False",
            "reason": source_note(target, count) + " No draw odds or probability value was invented.",
            "model_version": MODEL_VERSION,
            "rule_version": RULE_VERSION,
            "public_permits_2026": count["total"],
            "quota_source_status": "FULL_SPLIT",
            "quota_source_year": "2026",
            "quota_source_file": count["source_file"],
            "quota_2026_total": count["total"],
            "permit_allotment_2026_res": count["total"],
            "permit_allotment_2026_nr": "0",
            "permit_allotment_2026_total": count["total"],
            "permit_allotment_2026_source": SOURCE_AUTHORITY,
            "permit_allotment_2026_source_file": count["source_file"],
            "permit_allotment_2026_status": "FULL_SPLIT",
            "data_cutoff_date": DATA_CUTOFF_DATE,
            "reason_codes": "CONSERVATION_CODE_LOCK|FULL_SPLIT|NO_DRAW_PROBABILITY_INVENTED",
            "status": "conservation_reference_no_draw_odds",
            "trend": "not_modeled",
            "permit_availability_type": "desert_bighorn_conservation_reference",
            "probability_model": "NONE",
            "rule_status": "conservation_reference",
            "availability_status": "full_split",
            "data_quality_flags": "CONSERVATION_CODE_LOCK;NO_DRAW_PROBABILITY_MODELED;FULL_SPLIT",
            "prediction_year": "2026",
            "source_year": "2026",
            "applicant_forecast_method": "not_modeled_conservation_reference",
            "display_odds_text": "Conservation reference only; odds not modeled",
            "data_quality_grade": "A",
        }
    )
    return row


def update_file(path: Path, counts: dict[str, dict[str, str]], updater) -> dict[str, object]:
    fieldnames, rows = read_rows(path)
    touched = 0
    changed = 0
    updates: list[dict[str, str]] = []
    for row in rows:
        code = row.get("hunt_code", "").strip()
        if code not in TARGET_BY_CODE:
            continue
        touched += 1
        before = snapshot(row)
        updater(row, TARGET_BY_CODE[code], counts[code])
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


def promote_predictive_reference_rows(counts: dict[str, dict[str, str]]) -> dict[str, object]:
    fieldnames, rows = read_rows(PREDICTIVE)
    existing = {row.get("hunt_code", "") for row in rows}
    promoted: list[str] = []
    for code in sorted(MISSING_PREDICTIVE_CODES):
        if code in existing:
            continue
        rows.append(predictive_reference_row(fieldnames, TARGET_BY_CODE[code], counts[code]))
        promoted.append(code)

    touched = 0
    changed = 0
    updates: list[dict[str, str]] = []
    for row in rows:
        code = row.get("hunt_code", "").strip()
        if code not in TARGET_BY_CODE:
            continue
        touched += 1
        before = snapshot(row)
        common_updates(row, TARGET_BY_CODE[code], counts[code])
        if code in MISSING_PREDICTIVE_CODES:
            set_if_present(row, "model_version", MODEL_VERSION)
            set_if_present(row, "rule_version", RULE_VERSION)
            set_if_present(row, "modeled_by_engine", "False")
            set_if_present(row, "probability_model", "NONE")
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
        "promoted_codes": promoted,
        "updates": updates,
    }


def write_lock_csv(counts: dict[str, dict[str, str]]) -> None:
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
        "permit_source_authority",
        "permit_overlay_source",
        "source_row",
        "organization",
        "model_version",
        "rule_version",
        "note",
    ]
    rows = []
    for target in TARGETS:
        count = counts[target["hunt_code"]]
        rows.append(
            {
                "hunt_code": target["hunt_code"],
                "hunt_name": target["hunt_name"],
                "species": "Desert Bighorn Sheep",
                "sex_type": target["sex_type"],
                "weapon": "Any Legal Weapon",
                "hunt_type": target["hunt_type"],
                "season": target["season"],
                "Non Res": "0",
                "Res": count["total"],
                "Total": count["total"],
                "permit_status": "FULL_SPLIT",
                "permit_source_authority": SOURCE_AUTHORITY,
                "permit_overlay_source": count["source_file"],
                "source_row": count["source_page_or_row"],
                "organization": count["organization"] or count["group"],
                "model_version": "sportsman_existing_row" if target["hunt_code"] == "DS1000" else MODEL_VERSION,
                "rule_version": RULE_VERSION,
                "note": source_note(target, count),
            }
        )
    write_rows(LOCK_CSV, fieldnames, rows)


def validate_surface(path: Path) -> list[str]:
    _, rows = read_rows(path)
    grouped = {code: [] for code in TARGET_CODES}
    for row in rows:
        code = row.get("hunt_code", "").strip()
        if code in grouped:
            grouped[code].append(row)
    errors: list[str] = []
    for code in TARGET_CODES:
        if not grouped[code]:
            errors.append(f"{path}: missing {code}")
            continue
        for row in grouped[code]:
            for field in ["permits_2026_total", "permit_allotment_2026_total", "public_permits_2026", "quota_2026_total"]:
                if field in row and row[field] != "1":
                    errors.append(f"{path}: {code} {field} expected '1'")
            if "permits_2026_res" in row and row["permits_2026_res"] != "1":
                errors.append(f"{path}: {code} permits_2026_res expected '1'")
            if "permits_2026_nr" in row and row["permits_2026_nr"] != "0":
                errors.append(f"{path}: {code} permits_2026_nr expected '0'")
            if "permit_status" in row and row["permit_status"] != "FULL_SPLIT":
                errors.append(f"{path}: {code} permit_status expected FULL_SPLIT")
    return errors


def main() -> int:
    counts = conservation_counts()
    write_lock_csv(counts)
    results = [
        update_file(DATABASE, counts, common_updates),
        update_file(HUNT_MASTER, counts, common_updates),
        update_file(DRAW_REALITY, counts, common_updates),
        update_file(POINT_LADDER, counts, common_updates),
    ]
    predictive_result = promote_predictive_reference_rows(counts)
    results.append(predictive_result)

    runtime_updates = [update for result in results for update in result["updates"]]
    write_rows(RUNTIME_UPDATES_CSV, ["file", "hunt_code", "changed", "before", "after"], runtime_updates)

    validation_errors = []
    for path in [DATABASE, HUNT_MASTER, DRAW_REALITY, POINT_LADDER, PREDICTIVE]:
        validation_errors.extend(validate_surface(path))

    lock_rows = read_rows(LOCK_CSV)[1]
    duplicate_lock_codes = [
        code for code, count in Counter(row["hunt_code"] for row in lock_rows).items() if count > 1
    ]
    if duplicate_lock_codes:
        validation_errors.append(f"Duplicate lock rows: {duplicate_lock_codes}")

    summary = {
        "classification": "DESERT_BIGHORN_CONSERVATION_PERMIT_CODE_LOCK_2026",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "data_cutoff_date": DATA_CUTOFF_DATE,
        "lock_code_count": len(TARGETS),
        "lock_codes": [row["hunt_code"] for row in TARGETS],
        "conservation_source": str(CONSERVATION_CYCLE.relative_to(ROOT)).replace("\\", "/"),
        "all_locked_total": "1",
        "predictive_reference_codes_locked": sorted(MISSING_PREDICTIVE_CODES),
        "predictive_reference_code_count_locked": len(MISSING_PREDICTIVE_CODES),
        "predictive_reference_codes_added_this_run": predictive_result["promoted_codes"],
        "predictive_reference_code_count_added_this_run": len(predictive_result["promoted_codes"]),
        "target_surface_results": {
            str(result["path"].relative_to(ROOT)).replace("\\", "/"): {
                "row_count": result["row_count"],
                "rows_touched": result["touched"],
                "rows_changed": result["changed"],
            }
            for result in results
        },
        "runtime_update_row_count": len(runtime_updates),
        "lock_output": str(LOCK_CSV.relative_to(ROOT)).replace("\\", "/"),
        "runtime_updates_output": str(RUNTIME_UPDATES_CSV.relative_to(ROOT)).replace("\\", "/"),
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors,
        "blockers": len(validation_errors),
        "guardrail": "Desert bighorn conservation rows are locked as reference records; no draw odds, applicant counts, or probability values are invented.",
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Desert Bighorn Conservation Permit Code Lock 2026",
        "",
        f"- Lock codes: `{summary['lock_code_count']}`",
        f"- Predictive reference codes locked: `{summary['predictive_reference_code_count_locked']}`",
        f"- Runtime update rows: `{summary['runtime_update_row_count']}`",
        f"- Blockers: `{summary['blockers']}`",
        "",
        "## Locked Codes",
    ]
    for target in TARGETS:
        count = counts[target["hunt_code"]]
        lines.append(
            f"- `{target['hunt_code']}` {target['hunt_name']} - FULL_SPLIT - Res `{count['total']}`, Non Res `0`, Total `{count['total']}`"
        )
    lines.extend(["", "## Guardrail", str(summary["guardrail"])])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if validation_errors:
        for error in validation_errors:
            print(error)
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
