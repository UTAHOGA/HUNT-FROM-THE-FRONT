from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
GUIDEBOOK = ROOT / "data_truth/regulations_truth/normalized/2026_big_game_application_guidebook_hunt_tables.csv"
SUMMARY = ROOT / "processed_data/2026_big_game_predictive_v2_guidebook_promotion_summary.json"
DETAIL = ROOT / "processed_data/2026_big_game_predictive_v2_guidebook_promotion.csv"

SOURCE_FILE = "pipeline/RAW/hunt_unit_database/2026/pdf/regulations/2026 Big Game Application.pdf"
MODEL_VERSION = "guidebook_truth_reference_v1.0.0"
RULE_VERSION = "utah_guidebook_truth_promotion_v1.0.0"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def numeric(value: str) -> int | None:
    value = (value or "").strip().replace(",", "")
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def choose_residency(database_row: dict[str, str]) -> str:
    res = numeric(database_row.get("permits_2026_res", ""))
    nonres = numeric(database_row.get("permits_2026_nr", ""))
    if nonres and not res:
        return "Nonresident"
    return "Resident"


def build_reference_row(
    fieldnames: list[str],
    database_row: dict[str, str],
    guidebook_row: dict[str, str],
) -> dict[str, str]:
    row = {fieldname: "" for fieldname in fieldnames}
    total_permits = database_row.get("permits_2026_total", "")
    allotment_total = database_row.get("permit_allotment_2026_total", "") or total_permits
    detail_text = guidebook_row.get("guidebook_detail_text", "")
    season_text = database_row.get("season", "") or guidebook_row.get("guidebook_season_text", "")
    reason = (
        "Promoted from corrected 2026 Big Game Application Guidebook truth source because "
        "the hunt code was absent from draw_reality_engine_predictive_v2.csv; no draw-odds "
        "probability was invented."
    )

    row.update(
        {
            "year": "2026",
            "forecast_year": "2026",
            "hunt_code": database_row["hunt_code"],
            "hunt_name": database_row.get("hunt_name", "") or guidebook_row.get("guidebook_hunt_name", ""),
            "species": database_row.get("species", "") or guidebook_row.get("species_inferred", ""),
            "sex_type": database_row.get("sex_type", ""),
            "hunt_type": database_row.get("hunt_type", ""),
            "hunt_class": "Guidebook Truth Reference",
            "residency": choose_residency(database_row),
            "points": "0",
            "draw_pool": "guidebook_reference",
            "source_years_used": "2026",
            "source_year_count": "1",
            "latest_source_year": "2026",
            "earliest_source_year": "2026",
            "source_dataset": "2026_big_game_application_guidebook_hunt_tables",
            "model_strategy": "GUIDEBOOK_TRUTH_REFERENCE",
            "draw_system_type": "GUIDEBOOK_TRUTH_REFERENCE",
            "season_dates": season_text,
            "weapon": database_row.get("weapon", ""),
            "algorithm_status": "GUIDEBOOK_TRUTH_REFERENCE",
            "target_scope": "TARGET",
            "modeled_by_engine": "False",
            "reason": reason,
            "model_version": MODEL_VERSION,
            "rule_version": RULE_VERSION,
            "public_permits_2026": total_permits,
            "quota_source_status": "official_guidebook_reference",
            "quota_source_year": "2026",
            "quota_source_file": SOURCE_FILE,
            "quota_2026_total": total_permits,
            "permit_allotment_2026_res": database_row.get("permit_allotment_2026_res", "")
            or database_row.get("permits_2026_res", ""),
            "permit_allotment_2026_nr": database_row.get("permit_allotment_2026_nr", "")
            or database_row.get("permits_2026_nr", ""),
            "permit_allotment_2026_total": allotment_total,
            "permit_allotment_2026_source": database_row.get("permit_allotment_2026_source", ""),
            "permit_allotment_2026_source_file": database_row.get("permit_allotment_2026_source_file", "")
            or SOURCE_FILE,
            "permit_allotment_2026_status": database_row.get("permit_allotment_2026_status", "")
            or "official_guidebook_reference",
            "data_cutoff_date": "2026-05-24",
            "reason_codes": "GUIDEBOOK_TRUTH_SOURCE_ROW|NO_PREDICTIVE_DRAW_MODEL_ROW|PROMOTED_FROM_2026_BIG_GAME_APPLICATION_GUIDEBOOK",
            "status": "guidebook_truth_reference",
            "trend": "not_modeled",
            "permit_availability_type": "guidebook_reference",
            "probability_model": "NONE",
            "rule_status": "guidebook_truth_reference",
            "availability_status": "guidebook_truth_reference",
            "data_quality_flags": "PROMOTED_GUIDEBOOK_CODE;NO_DRAW_PROBABILITY_MODELED",
            "prediction_year": "2026",
            "source_year": "2026",
            "applicant_forecast_method": "not_modeled_guidebook_truth_reference",
            "display_odds_text": "Guidebook reference only; odds not modeled",
            "data_quality_grade": "A",
        }
    )

    if "source_note" in row:
        row["source_note"] = detail_text
    return row


def main() -> int:
    predictive_rows = read_rows(PREDICTIVE)
    database_rows = {row["hunt_code"]: row for row in read_rows(DATABASE)}
    guidebook_rows = {row["hunt_code"]: row for row in read_rows(GUIDEBOOK)}

    with PREDICTIVE.open(newline="", encoding="utf-8-sig") as handle:
        fieldnames = csv.DictReader(handle).fieldnames or []

    guidebook_codes = set(guidebook_rows)
    existing_codes = {row.get("hunt_code", "") for row in predictive_rows}
    missing_codes = sorted(guidebook_codes - existing_codes)

    blockers: list[dict[str, str]] = []
    promoted_rows: list[dict[str, str]] = []
    detail_rows: list[dict[str, str]] = []
    for code in missing_codes:
        database_row = database_rows.get(code)
        guidebook_row = guidebook_rows.get(code)
        if not database_row or not guidebook_row:
            blockers.append(
                {
                    "hunt_code": code,
                    "blocker": "missing_database_or_guidebook_truth_row",
                    "database_present": str(bool(database_row)).lower(),
                    "guidebook_present": str(bool(guidebook_row)).lower(),
                }
            )
            continue
        promoted = build_reference_row(fieldnames, database_row, guidebook_row)
        promoted_rows.append(promoted)
        detail_rows.append(
            {
                "hunt_code": code,
                "hunt_name": promoted["hunt_name"],
                "species": promoted["species"],
                "hunt_type": promoted["hunt_type"],
                "residency": promoted["residency"],
                "permits_2026_total": promoted["permit_allotment_2026_total"],
                "guidebook_page": guidebook_row.get("guidebook_page", ""),
                "promotion_status": "PROMOTED" if promoted else "BLOCKED",
                "reason": promoted["reason"],
            }
        )

    if blockers:
        detail_rows.extend(
            {
                "hunt_code": blocker["hunt_code"],
                "hunt_name": "",
                "species": "",
                "hunt_type": "",
                "residency": "",
                "permits_2026_total": "",
                "guidebook_page": "",
                "promotion_status": "BLOCKED",
                "reason": blocker["blocker"],
            }
            for blocker in blockers
        )

    if promoted_rows:
        predictive_rows.extend(promoted_rows)
        write_rows(PREDICTIVE, fieldnames, predictive_rows)

    final_codes = {row.get("hunt_code", "") for row in predictive_rows}
    still_missing = sorted(guidebook_codes - final_codes)
    promoted_reference_rows = [
        row
        for row in predictive_rows
        if row.get("model_version") == MODEL_VERSION and row.get("hunt_code", "") in guidebook_codes
    ]
    promoted_reference_codes = sorted({row["hunt_code"] for row in promoted_reference_rows})
    stable_detail_rows = []
    for row in sorted(promoted_reference_rows, key=lambda item: item["hunt_code"]):
        guidebook_row = guidebook_rows[row["hunt_code"]]
        stable_detail_rows.append(
            {
                "hunt_code": row["hunt_code"],
                "hunt_name": row.get("hunt_name", ""),
                "species": row.get("species", ""),
                "hunt_type": row.get("hunt_type", ""),
                "residency": row.get("residency", ""),
                "permits_2026_total": row.get("permit_allotment_2026_total", ""),
                "guidebook_page": guidebook_row.get("guidebook_page", ""),
                "promotion_status": "PROMOTED",
                "reason": row.get("reason", ""),
            }
        )
    stable_detail_rows.extend(row for row in detail_rows if row["promotion_status"] != "PROMOTED")
    write_rows(
        DETAIL,
        [
            "hunt_code",
            "hunt_name",
            "species",
            "hunt_type",
            "residency",
            "permits_2026_total",
            "guidebook_page",
            "promotion_status",
            "reason",
        ],
        stable_detail_rows,
    )
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
            for row in predictive_rows
        ).items()
        if count > 1
    ]

    summary = {
        "classification": "GUIDEBOOK_TRUTH_REFERENCE_PROMOTION",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_truth": str(GUIDEBOOK.relative_to(ROOT)).replace("\\", "/"),
        "target_surface": str(PREDICTIVE.relative_to(ROOT)).replace("\\", "/"),
        "initial_missing_hunt_code_count": len(missing_codes),
        "newly_promoted_hunt_code_count": len(promoted_rows),
        "promoted_hunt_code_count": len(promoted_reference_codes),
        "blocked_hunt_code_count": len(blockers),
        "still_missing_hunt_code_count": len(still_missing),
        "duplicate_reference_key_count": len(duplicate_keys),
        "promoted_hunt_codes": promoted_reference_codes,
        "still_missing_hunt_codes": still_missing,
        "blockers": blockers,
        "guardrail": "Guidebook truth rows promote hunt-code and permit-reference data only; draw odds remain unmodeled.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    if blockers or still_missing or duplicate_keys:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
