"""Year-by-year hardening audit for draw-results truth data.

This is the draw-side companion to the harvest hardening audit. It records
unique hunt-code coverage by draw year without merging draw data into harvest
or prediction feature surfaces.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
DRAW_LONG = ROOT / "data_truth" / "draw_results_truth" / "normalized" / "draw_results_long.csv"
VALIDATION_DIR = ROOT / "data_truth" / "draw_results_truth" / "validation"
YEAR_CSV = VALIDATION_DIR / "draw_year_by_year_hardening_2026.csv"
SUMMARY_JSON = VALIDATION_DIR / "draw_year_by_year_hardening_2026_summary.json"
MISSING_CSV = VALIDATION_DIR / "draw_year_by_year_hardening_2026_missing_codes.csv"
REPORT_MD = ROOT / "processed_data" / "draw_year_by_year_hardening_2026.md"

DRAW_FIELDS_OF_VALUE = [
    "eligible_applicants",
    "total_drawn",
    "bonus_permits",
    "regular_permits",
    "total_permits",
    "success_ratio",
    "p_draw_percent",
    "residency",
    "points",
    "draw_pool",
    "draw_method",
    "hunt_class",
    "source_file",
    "page_number",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def csv_fields(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle).fieldnames or [])


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def norm(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def year_value(row: dict[str, str]) -> str:
    return norm(row.get("year") or row.get("draw_year") or row.get("reported_hunt_year_inferred") or row.get("publish_year"))


def has_value(value: str | None) -> bool:
    return bool(norm(value))


def classify_missing(row: dict[str, str], covered_any_year: bool) -> str:
    joined = " ".join(
        [
            row.get("hunt_type", ""),
            row.get("hunt_class", ""),
            row.get("hunt_name", ""),
            row.get("weapon", ""),
            row.get("NOTES", ""),
        ]
    ).lower()
    if not covered_any_year:
        if any(token in joined for token in ["statewide", "expo", "conservation", "sportsman"]):
            return "SPECIAL_OR_STATEWIDE_ROW_NEEDS_DRAW_SOURCE_REVIEW"
        if "private land" in joined or "private lands" in joined or "landowner" in joined:
            return "PRIVATE_LAND_OR_LANDOWNER_ROW_NEEDS_DRAW_SOURCE_REVIEW"
        if "cwmu" in joined:
            return "CWMU_ROW_NEEDS_DRAW_SOURCE_REVIEW"
        return "CURRENT_CODE_HAS_NO_DRAW_HISTORY_REVIEW"
    return "NO_DRAW_ROW_FOR_THIS_DRAW_YEAR"


def build_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Draw Year-By-Year Hardening Audit 2026",
        "",
        "Read-only audit of normalized draw-results truth against the current 2026 canonical hunt-code universe.",
        "",
        "## Topline",
        "",
        f"- Current DATABASE hunt codes: {summary['current_database_unique_hunt_codes']}",
        f"- Draw long rows: {summary['draw_long_rows']}",
        f"- Unique draw hunt codes across all years: {summary['unique_draw_hunt_codes_all_years']}",
        f"- Current codes covered in at least one draw year: {summary['current_database_codes_covered_any_draw_year']}",
        f"- Current codes missing from all draw years: {summary['current_database_codes_missing_all_draw_years']}",
        "- Expected trend: unique draw hunt-code count should generally increase slightly year over year, or any drop should be explained by source coverage, discontinued codes, split/renamed hunt codes, or true season structure changes.",
        "",
        "## Year Coverage",
        "",
        "| Draw year | Native unique draw codes | Draw rows |",
        "|---|---:|---:|",
    ]
    for row in summary["year_rows"]:
        lines.append(
            "| {year} | {codes} | {rows} |".format(
                year=row["draw_year"],
                rows=row["draw_rows"],
                codes=row["native_unique_draw_hunt_codes"],
            )
        )
    lines.extend(
        [
            "",
            "## Current Reference Alignment",
            "",
            "The 2026 `DATABASE.csv` comparison is only for crosswalk/alignment work. It is not a completeness score for older draw years.",
            "",
            "| Draw year | Current 2026 codes cross-referenced | Current 2026 codes not cross-referenced |",
            "|---|---:|---:|",
        ]
    )
    for row in summary["year_rows"]:
        lines.append(
            "| {year} | {covered} | {missing} |".format(
                year=row["draw_year"],
                covered=row["current_database_codes_covered"],
                missing=row["current_database_codes_missing"],
            )
        )
    lines.extend(
        [
            "",
            "## Data-Land Rule",
            "",
            "- Draw odds/results stay in `data_truth/draw_results_truth` until a later feature-combine step.",
            "- Harvest metrics stay in `data_truth/harvest_results_truth` until a later feature-combine step.",
            "- Prediction features should combine these only after each domain has year-by-year coverage and source lineage.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    database_rows = read_rows(DATABASE)
    draw_rows = read_rows(DRAW_LONG)
    current_by_code = {norm(row.get("hunt_code")): row for row in database_rows if norm(row.get("hunt_code"))}
    current_codes = set(current_by_code)
    draw_codes_all_years = {norm(row.get("hunt_code")) for row in draw_rows if norm(row.get("hunt_code"))}
    current_codes_covered_any_year = current_codes & draw_codes_all_years
    years = sorted({year_value(row) for row in draw_rows if year_value(row)})
    fields = set(csv_fields(DRAW_LONG))

    rows_by_year: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in draw_rows:
        year = year_value(row)
        if year:
            rows_by_year[year].append(row)

    year_rows: list[dict[str, str]] = []
    missing_rows: list[dict[str, str]] = []
    for year in years:
        rows = rows_by_year[year]
        year_codes = {norm(row.get("hunt_code")) for row in rows if norm(row.get("hunt_code"))}
        current_covered = year_codes & current_codes
        current_missing = current_codes - current_covered
        residency_counts = Counter(norm(row.get("residency")) for row in rows)
        status_counts = Counter(norm(row.get("status")) for row in rows)
        draw_pool_counts = Counter(norm(row.get("draw_pool")) for row in rows)
        draw_method_counts = Counter(norm(row.get("draw_method")) for row in rows)

        year_rows.append(
            {
                "draw_year": year,
                "model_target_year": str(int(year) + 1) if year.isdigit() else "",
                "draw_rows": str(len(rows)),
                "native_unique_draw_hunt_codes": str(len(year_codes)),
                "current_database_hunt_codes": str(len(current_codes)),
                "current_database_codes_covered": str(len(current_covered)),
                "current_database_codes_missing": str(len(current_missing)),
                "current_database_coverage_pct": f"{(len(current_covered) / len(current_codes) * 100):.2f}",
                "current_database_comparison_use": "CROSS_REFERENCE_ONLY_NOT_YEAR_COMPLETENESS",
                "historical_only_draw_codes": str(len(year_codes - current_codes)),
                "residency_counts": "|".join(f"{key}:{residency_counts[key]}" for key in sorted(residency_counts) if key),
                "status_counts": "|".join(f"{key}:{status_counts[key]}" for key in sorted(status_counts) if key),
                "draw_pool_counts": "|".join(f"{key}:{draw_pool_counts[key]}" for key in sorted(draw_pool_counts) if key),
                "draw_method_counts": "|".join(f"{key}:{draw_method_counts[key]}" for key in sorted(draw_method_counts) if key),
            }
        )
        for code in sorted(current_missing):
            db_row = current_by_code[code]
            covered_any_year = code in current_codes_covered_any_year
            missing_rows.append(
                {
                    "draw_year": year,
                    "expected_model_target_year": str(int(year) + 1) if year.isdigit() else "",
                    "hunt_code": code,
                    "boundary_id": db_row.get("boundary_id", ""),
                    "species": db_row.get("species", ""),
                    "sex_type": db_row.get("sex_type", ""),
                    "hunt_name": db_row.get("hunt_name", ""),
                    "hunt_type": db_row.get("hunt_type", ""),
                    "hunt_class": db_row.get("hunt_class", ""),
                    "weapon": db_row.get("weapon", ""),
                    "covered_in_any_draw_year": "YES" if covered_any_year else "NO",
                    "missing_reason": classify_missing(db_row, covered_any_year),
                }
            )

    field_rows = [
        {
            "field": field,
            "captured_in_draw_truth": field in fields,
            "nonblank_rows": sum(1 for row in draw_rows if has_value(row.get(field))),
        }
        for field in DRAW_FIELDS_OF_VALUE
    ]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "audit_scope": "read_only_draw_truth_year_by_year_hardening",
        "database_path": str(DATABASE.relative_to(ROOT)),
        "draw_long_path": str(DRAW_LONG.relative_to(ROOT)),
        "current_database_rows": len(database_rows),
        "current_database_unique_hunt_codes": len(current_codes),
        "draw_long_rows": len(draw_rows),
        "unique_draw_years": years,
        "unique_draw_hunt_codes_all_years": len(draw_codes_all_years),
        "current_database_codes_covered_any_draw_year": len(current_codes_covered_any_year),
        "current_database_codes_missing_all_draw_years": len(current_codes - current_codes_covered_any_year),
        "historical_only_draw_codes_not_current_database": len(draw_codes_all_years - current_codes),
        "draw_hunt_code_growth_note": (
            "Unique draw hunt-code counts should generally increase slightly year over year, "
            "or the audit must explain the gap before draw data is combined into prediction features."
        ),
        "field_capture_status": field_rows,
        "year_rows": year_rows,
        "missing_code_rows": len(missing_rows),
        "blocker_count": 0,
        "guardrails": [
            "Read-only audit: no draw truth rows, DATABASE.csv values, website feeds, or prediction files are modified.",
            "Draw odds/results remain draw-domain evidence until a later feature-combine step.",
            "Harvest and draw data must be hardened year by year before combined prediction features are published.",
            "Do not judge historical draw years against the 2026 active hunt-code count as a completeness score; the 2026 database comparison is cross-reference evidence only.",
        ],
        "outputs": {
            "year_coverage_csv": str(YEAR_CSV.relative_to(ROOT)),
            "missing_codes_csv": str(MISSING_CSV.relative_to(ROOT)),
            "summary_json": str(SUMMARY_JSON.relative_to(ROOT)),
            "summary_md": str(REPORT_MD.relative_to(ROOT)),
        },
    }

    write_rows(YEAR_CSV, year_rows, list(year_rows[0].keys()) if year_rows else [])
    write_rows(
        MISSING_CSV,
        missing_rows,
        [
            "draw_year",
            "expected_model_target_year",
            "hunt_code",
            "boundary_id",
            "species",
            "sex_type",
            "hunt_name",
            "hunt_type",
            "hunt_class",
            "weapon",
            "covered_in_any_draw_year",
            "missing_reason",
        ],
    )
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(build_markdown(summary), encoding="utf-8")
    print(
        "Draw hardening audit complete: "
        f"{len(current_codes_covered_any_year)}/{len(current_codes)} current codes covered in at least one draw year; "
        f"{len(current_codes - current_codes_covered_any_year)} need all-year draw review."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
