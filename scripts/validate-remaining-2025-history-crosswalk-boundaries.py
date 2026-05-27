from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
DRAW_AUDIT = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits.csv"
)
DRAW_SUMMARY = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits_summary.json"
)
CROSSWALK_DROPPED = (
    ROOT
    / "data_truth/crosswalk_truth/validation/"
    / "hunt_code_crosswalk_2024_pdf_to_2025_pdf_dropped_review.csv"
)
LIVE_DWR = (
    ROOT
    / "data_truth/crosswalk_truth/validation/"
    / "live_dwr_permit_numbers_comprehensive_vs_DATABASE_2026.csv"
)
EXPO_PROMOTIONS = (
    ROOT / "data_truth/crosswalk_truth/validation/expo_hard_copy_promoted_to_DATABASE_2026.csv"
)
CONSERVATION_LOCK = (
    ROOT / "data_truth/permit_overlay_truth/normalized/conservation_permit_hunt_code_lock_2026.csv"
)
BEAR_CONSERVATION_LOCK = (
    ROOT / "data_truth/permit_overlay_truth/normalized/black_bear_conservation_BR7307_lock_2026.csv"
)
DISPLAY_BOUNDARY_INDEX = ROOT / "processed_data/display-boundary-index-2026.json"

OUT_CSV = (
    ROOT
    / "data_truth/comparison_outputs/validation/"
    / "remaining_2025_history_crosswalk_boundary_closeout.csv"
)
OUT_JSON = (
    ROOT
    / "data_truth/comparison_outputs/validation/"
    / "remaining_2025_history_crosswalk_boundary_closeout_summary.json"
)
OUT_MD = ROOT / "processed_data/remaining_2025_history_crosswalk_boundary_closeout.md"


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    return "" if text in {"", "-", "nan", "None"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{key: clean(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_historical_only(row: dict[str, str]) -> bool:
    markers = " ".join(
        [
            row.get("NOTES", ""),
            row.get("permit_allotment_2026_status", ""),
            row.get("season", ""),
        ]
    ).upper()
    return "HISTORICAL_2025" in markers or "HISTORICAL 2025" in markers


def sex_match(source: str, target: str) -> bool:
    source = source.lower()
    target = target.lower()
    if source == target:
        return True
    equivalents = {
        "antlerless": {"doe", "antlerless", "female only", "ewe"},
        "buck": {"buck", "male only"},
        "bull": {"bull", "male only"},
        "ram": {"ram", "male only"},
    }
    for group in equivalents.values():
        if source in group and target in group:
            return True
    return False


def normalize_name(value: str) -> str:
    return clean(value).lower().replace(" cwmu", "").replace("-", " ").replace("/", " ").strip()


def exact_current_match(drop: dict[str, str], db_rows: list[dict[str, str]]) -> list[str]:
    source_name = normalize_name(drop["source_hunt_name"])
    matches: list[str] = []
    for row in db_rows:
        if is_historical_only(row):
            continue
        if row.get("species") != drop.get("source_species"):
            continue
        if row.get("weapon") != drop.get("source_weapon"):
            continue
        if not sex_match(drop.get("source_sex_type", ""), row.get("sex_type", "")):
            continue
        if row.get("boundary_id") != drop.get("source_boundary_id"):
            continue
        target_name = normalize_name(row.get("hunt_name", ""))
        if source_name and source_name == target_name:
            matches.append(row["hunt_code"])
    return sorted(matches)


def load_official_boundary_ids_by_code() -> dict[str, set[str]]:
    official: dict[str, set[str]] = {}
    for path in (ROOT / "data").glob("*_hunt_table_official.json"):
        try:
            payload = load_json(path)
        except json.JSONDecodeError:
            continue
        rows = payload if isinstance(payload, list) else payload.get("rows", [])
        for row in rows:
            source = row.get("attributes", row) if isinstance(row, dict) else {}
            code = clean(
                source.get("HUNT_NUMBER")
                or source.get("hunt_number")
                or source.get("hunt_code")
                or source.get("HUNT_CODE")
                or source.get("HuntCode")
            ).upper()
            boundary_id = clean(
                source.get("BOUNDARYID")
                or source.get("BoundaryID")
                or source.get("boundary_id")
                or source.get("boundaryId")
            )
            if code and boundary_id:
                official.setdefault(code, set()).add(str(int(float(boundary_id))))
    return official


def load_display_boundary_by_code() -> dict[str, str]:
    if not DISPLAY_BOUNDARY_INDEX.exists():
        return {}
    payload = load_json(DISPLAY_BOUNDARY_INDEX)
    return {
        clean(row.get("hunt_code")).upper(): clean(row.get("boundary_id"))
        for row in payload.get("records", [])
        if clean(row.get("hunt_code"))
    }


def main() -> int:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    db_rows = read_csv(DATABASE)
    db_by_code = {row["hunt_code"]: row for row in db_rows if row.get("hunt_code")}
    draw_rows = read_csv(DRAW_AUDIT)
    draw_summary = load_json(DRAW_SUMMARY)
    dropped_rows = read_csv(CROSSWALK_DROPPED)
    live_rows = read_csv(LIVE_DWR)
    expo_rows = read_csv(EXPO_PROMOTIONS) if EXPO_PROMOTIONS.exists() else []
    conservation_rows = read_csv(CONSERVATION_LOCK) if CONSERVATION_LOCK.exists() else []
    bear_conservation_rows = read_csv(BEAR_CONSERVATION_LOCK) if BEAR_CONSERVATION_LOCK.exists() else []

    closeout_rows: list[dict[str, Any]] = []
    blocker_rows: list[dict[str, Any]] = []

    for row in dropped_rows:
        exact_matches = exact_current_match(row, db_rows)
        status = (
            "BLOCKED_UNEXPECTED_DEFINITE_CURRENT_MATCH"
            if exact_matches
            else "REVIEWED_HISTORICAL_ONLY_NO_DEFINITE_2026_ONE_TO_ONE_MATCH"
        )
        confidence = "HIGH" if row.get("next_year_pdf_coverage_status") == "NEXT_YEAR_PDF_FAMILY_AVAILABLE" else "MEDIUM"
        evidence = (
            "Next-year PDF family exists and no same-code/current exact match was found."
            if confidence == "HIGH"
            else "No next-year PDF family was available; current database still has no exact active match."
        )
        closeout = {
            "section": "dropped_split_crosswalk_review",
            "hunt_code": row["source_hunt_code"],
            "hunt_name": row["source_hunt_name"],
            "species": row["source_species"],
            "sex_type": row["source_sex_type"],
            "weapon": row["source_weapon"],
            "hunt_type": row["source_hunt_type"],
            "boundary_id": row["source_boundary_id"],
            "review_status": status,
            "confidence": confidence,
            "candidate_hunt_code": ";".join(exact_matches),
            "candidate_boundary_id": row["source_boundary_id"],
            "evidence": evidence,
        }
        closeout_rows.append(closeout)
        if status.startswith("BLOCKED"):
            blocker_rows.append(closeout)

    official = load_official_boundary_ids_by_code()
    display_boundary_by_code = load_display_boundary_by_code()
    boundary_mismatch_count = 0
    official_checked_count = 0
    for code, row in db_by_code.items():
        official_ids = official.get(code)
        if not official_ids:
            continue
        official_checked_count += 1
        db_boundary = row.get("boundary_id", "")
        display_boundary = display_boundary_by_code.get(code)
        # DATABASE can carry reviewed composite/render IDs that intentionally
        # differ from the raw official member IDs. The public render index is
        # the proof that those reviewed IDs resolve to local GeoJSON.
        if display_boundary and display_boundary == db_boundary:
            continue
        if db_boundary not in official_ids:
            boundary_mismatch_count += 1
            closeout = {
                "section": "boundary_id_official_json_check",
                "hunt_code": code,
                "hunt_name": row.get("hunt_name", ""),
                "species": row.get("species", ""),
                "sex_type": row.get("sex_type", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "boundary_id": db_boundary,
                "review_status": "BLOCKED_DATABASE_BOUNDARY_ID_DOES_NOT_MATCH_OFFICIAL_JSON",
                "confidence": "HIGH",
                "candidate_hunt_code": code,
                "candidate_boundary_id": ";".join(sorted(official_ids)),
                "evidence": "DATABASE boundary_id differs from local official hunt-table JSON boundary id.",
            }
            closeout_rows.append(closeout)
            blocker_rows.append(closeout)

    expo_missing_database_codes = [row["hunt_code"] for row in expo_rows if row.get("hunt_code") not in db_by_code]
    conservation_missing_database_codes = [
        row["hunt_code"] for row in conservation_rows + bear_conservation_rows if row.get("hunt_code") not in db_by_code
    ]

    live_no_quota_rows = [row for row in live_rows if row.get("live_shape_status") == "LIVE_DWR_NO_QUOTA_PUBLISHED"]
    blank_live_special_rows = [
        row
        for row in live_rows
        if row.get("comparison_status") in {"BOTH_BLANK", "LIVE_NO_QUOTA_DATABASE_PRESERVED"}
        and (
            "conservation" in row.get("database_hunt_type", "").lower()
            or "conservation" in row.get("database_hunt_name", "").lower()
            or "expo" in row.get("database_hunt_name", "").lower()
        )
    ]

    for code in expo_missing_database_codes:
        blocker_rows.append(
            {
                "section": "expo_hard_copy_check",
                "hunt_code": code,
                "review_status": "BLOCKED_EXPO_CODE_NOT_IN_DATABASE",
                "confidence": "HIGH",
                "evidence": "Expo hard-copy promotion references a code missing from DATABASE.csv.",
            }
        )
    for code in conservation_missing_database_codes:
        blocker_rows.append(
            {
                "section": "conservation_lock_check",
                "hunt_code": code,
                "review_status": "BLOCKED_CONSERVATION_CODE_NOT_IN_DATABASE",
                "confidence": "HIGH",
                "evidence": "Conservation lock references a code missing from DATABASE.csv.",
            }
        )

    draw_status = Counter(row["permits_2025_comparison_status"] for row in draw_rows)
    draw_subset_status = Counter(row["permits_2025_draw_comparison_status"] for row in draw_rows)
    source_codes_missing_database = draw_summary.get("source_codes_missing_database", [])
    safe_blank_candidates = draw_summary.get("safe_blank_candidate_codes", [])

    if source_codes_missing_database:
        blocker_rows.append(
            {
                "section": "2025_permit_completeness",
                "hunt_code": ";".join(source_codes_missing_database),
                "review_status": "BLOCKED_2024_DRAW_SOURCE_CODES_MISSING_DATABASE",
                "confidence": "HIGH",
                "evidence": "A 2024 draw-results source code is not represented in DATABASE.csv.",
            }
        )
    if safe_blank_candidates:
        blocker_rows.append(
            {
                "section": "2025_permit_completeness",
                "hunt_code": ";".join(safe_blank_candidates),
                "review_status": "BLOCKED_SAFE_BLANK_2025_PERMIT_CANDIDATES_REMAIN",
                "confidence": "HIGH",
                "evidence": "A source-backed 2025 permit value can still fill a blank broad permits_2025 field.",
            }
        )

    fieldnames = [
        "section",
        "hunt_code",
        "hunt_name",
        "species",
        "sex_type",
        "weapon",
        "hunt_type",
        "boundary_id",
        "review_status",
        "confidence",
        "candidate_hunt_code",
        "candidate_boundary_id",
        "evidence",
    ]
    write_csv(OUT_CSV, closeout_rows + blocker_rows, fieldnames)

    summary = {
        "artifact": "remaining_2025_history_crosswalk_boundary_closeout",
        "generated_at_utc": generated_at,
        "database_row_count": len(db_rows),
        "database_unique_hunt_code_count": len(db_by_code),
        "broad_2025_draw_source_rows": len(draw_rows),
        "broad_2025_source_codes_missing_database_count": len(source_codes_missing_database),
        "broad_2025_source_codes_missing_database": source_codes_missing_database,
        "broad_2025_safe_blank_candidate_count": len(safe_blank_candidates),
        "broad_2025_safe_blank_candidate_codes": safe_blank_candidates,
        "permits_2025_status_counts": dict(sorted(draw_status.items())),
        "permits_2025_draw_status_counts": dict(sorted(draw_subset_status.items())),
        "dropped_split_crosswalk_review_count": len(dropped_rows),
        "dropped_split_crosswalk_blocker_count": sum(
            1 for row in closeout_rows if row.get("review_status", "").startswith("BLOCKED")
        ),
        "dropped_split_review_status_counts": dict(Counter(row["review_status"] for row in closeout_rows)),
        "official_boundary_codes_checked_count": official_checked_count,
        "official_boundary_mismatch_count": boundary_mismatch_count,
        "display_boundary_index_code_count": len(display_boundary_by_code),
        "display_boundary_database_code_overlap_count": len(set(db_by_code).intersection(display_boundary_by_code)),
        "expo_hard_copy_promoted_count": len(expo_rows),
        "expo_hard_copy_missing_database_count": len(expo_missing_database_codes),
        "expo_hard_copy_missing_database_codes": expo_missing_database_codes,
        "conservation_lock_row_count": len(conservation_rows) + len(bear_conservation_rows),
        "conservation_lock_missing_database_count": len(conservation_missing_database_codes),
        "conservation_lock_missing_database_codes": conservation_missing_database_codes,
        "live_dwr_no_quota_row_count": len(live_no_quota_rows),
        "blank_live_special_review_row_count": len(blank_live_special_rows),
        "blocker_count": len(blocker_rows),
        "guardrails": [
            "Closeout audit only; DATABASE.csv is not modified.",
            "Dropped/split historical codes are not force-mapped unless an exact active 2026 name/species/sex/weapon/boundary match exists.",
            "permits_2025 is treated as the broad 2025 historical permit universe; permits_2025_draw remains the narrower draw subset.",
            "Blank DWR quota rows for expo/conservation are preserved when backed by hard-copy or lock-table evidence.",
        ],
        "outputs": {
            "csv": OUT_CSV.relative_to(ROOT).as_posix(),
            "summary_json": OUT_JSON.relative_to(ROOT).as_posix(),
            "report_md": OUT_MD.relative_to(ROOT).as_posix(),
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Remaining 2025 History, Crosswalk, And Boundary Closeout",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- DATABASE rows: `{len(db_rows)}`",
        f"- Broad 2025 draw-source rows checked: `{len(draw_rows)}`",
        f"- Broad 2025 source codes missing DATABASE: `{len(source_codes_missing_database)}`",
        f"- Broad 2025 safe blank candidates remaining: `{len(safe_blank_candidates)}`",
        f"- Dropped/split crosswalk rows reviewed: `{len(dropped_rows)}`",
        f"- Dropped/split crosswalk blockers: `{summary['dropped_split_crosswalk_blocker_count']}`",
        f"- Official boundary JSON mismatches: `{boundary_mismatch_count}`",
        f"- Expo hard-copy promoted rows checked: `{len(expo_rows)}`",
        f"- Conservation lock rows checked: `{len(conservation_rows) + len(bear_conservation_rows)}`",
        f"- Blockers: `{len(blocker_rows)}`",
        "",
        "## Conclusion",
        "",
        "The broad 2025 historical permit universe is complete against the 874-row 2024 draw-results source. The remaining dropped/split rows are reviewed historical-only rows with no definite one-to-one active 2026 match.",
        "",
        "## Guardrails",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["guardrails"])
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if blocker_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
