"""Year-by-year hardening audit for the harvest truth database.

This is a read-only audit. It does not rebuild harvest extracts, change
DATABASE.csv, or promote harvest numbers into permit/allotment fields.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
BEST = ROOT / "data_truth" / "harvest_results_truth" / "normalized" / "harvest_quality_features_all_years_by_hunt_code.csv"
LONG = ROOT / "data_truth" / "harvest_results_truth" / "normalized" / "harvest_results_all_years_long.csv"
METRIC_AUDIT = ROOT / "processed_data" / "harvest_results_database_metric_integrity_audit.csv"
VALIDATION_DIR = ROOT / "data_truth" / "harvest_results_truth" / "validation"
SUMMARY_JSON = VALIDATION_DIR / "harvest_year_by_year_hardening_2026_summary.json"
YEAR_CSV = VALIDATION_DIR / "harvest_year_by_year_hardening_2026.csv"
MISSING_CSV = VALIDATION_DIR / "harvest_year_by_year_hardening_2026_missing_codes.csv"
HISTORICAL_ONLY_CSV = VALIDATION_DIR / "harvest_year_by_year_hardening_2026_historical_only_codes.csv"
REPORT_MD = ROOT / "processed_data" / "harvest_year_by_year_hardening_2026.md"

NUMERIC_FIELDS = [
    "permits",
    "hunters_afield",
    "harvest_total",
    "harvest_male",
    "harvest_female",
    "harvest_young",
    "percent_success",
    "average_days",
    "hunter_satisfaction",
    "average_age",
    "harvest_objective",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def has_number(value: str | None) -> bool:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return False
    try:
        float(text)
        return True
    except ValueError:
        return False


def norm(text: str | None) -> str:
    return " ".join(str(text or "").strip().split())


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
            return "SPECIAL_OR_STATEWIDE_ROW_NEEDS_SOURCE_REVIEW"
        if "private land" in joined or "private lands" in joined or "landowner" in joined:
            return "PRIVATE_LAND_OR_LANDOWNER_ROW_NEEDS_SOURCE_REVIEW"
        if "cwmu" in joined:
            return "CWMU_ROW_NEEDS_SOURCE_REVIEW"
        return "CURRENT_CODE_HAS_NO_HARVEST_HISTORY_REVIEW"
    return "NO_HARVEST_ROW_FOR_THIS_REPORTED_YEAR"


def pipe_counter(values: Counter[str]) -> str:
    return "|".join(f"{key}:{values[key]}" for key in sorted(values) if key)


def metric_issue_counts() -> tuple[Counter[str], Counter[str]]:
    issues_by_year: Counter[str] = Counter()
    success_conflicts_by_year: Counter[str] = Counter()
    if not METRIC_AUDIT.exists():
        return issues_by_year, success_conflicts_by_year
    for row in read_rows(METRIC_AUDIT):
        year = norm(row.get("reported_hunt_year"))
        if not year:
            continue
        issues_by_year[year] += 1
        if "SUCCESS_RATE_MATH_CONFLICT" in row.get("flags", ""):
            success_conflicts_by_year[year] += 1
    return issues_by_year, success_conflicts_by_year


def main() -> int:
    database_rows = read_rows(DATABASE)
    best_rows = read_rows(BEST)
    long_rows = read_rows(LONG)

    current_by_code = {norm(row.get("hunt_code")): row for row in database_rows if norm(row.get("hunt_code"))}
    current_codes = set(current_by_code)
    harvest_codes_all_years = {norm(row.get("hunt_code")) for row in best_rows if norm(row.get("hunt_code"))}
    current_codes_covered_any_year = current_codes & harvest_codes_all_years
    historical_only_codes = sorted(harvest_codes_all_years - current_codes)
    years = sorted({norm(row.get("reported_hunt_year")) for row in best_rows if norm(row.get("reported_hunt_year"))})
    issues_by_year, success_conflicts_by_year = metric_issue_counts()

    best_by_year: dict[str, list[dict[str, str]]] = defaultdict(list)
    long_by_year: Counter[str] = Counter()
    for row in best_rows:
        best_by_year[norm(row.get("reported_hunt_year"))].append(row)
    for row in long_rows:
        long_by_year[norm(row.get("reported_hunt_year"))] += 1

    year_rows: list[dict[str, str]] = []
    missing_rows: list[dict[str, str]] = []
    for year in years:
        rows = best_by_year[year]
        year_codes = {norm(row.get("hunt_code")) for row in rows if norm(row.get("hunt_code"))}
        current_covered = year_codes & current_codes
        current_missing = current_codes - current_covered
        source_status = Counter(norm(row.get("source_status")) for row in rows)
        parse_status = Counter(norm(row.get("parse_status")) for row in rows)
        species_counts = Counter(norm(row.get("species")) for row in rows)
        model_target_years = sorted({norm(row.get("model_target_year")) for row in rows if norm(row.get("model_target_year"))})
        guardrail_rows = sum(
            1
            for row in rows
            if norm(row.get("do_not_use_for_permit_quota")) == "True"
            and norm(row.get("do_not_use_directly_for_p_draw")) == "True"
        )

        numeric_counts = {
            f"{field}_numeric_rows": str(sum(1 for row in rows if has_number(row.get(field))))
            for field in NUMERIC_FIELDS
        }

        year_rows.append(
            {
                "reported_hunt_year": year,
                "model_target_years": "|".join(model_target_years),
                "best_rows": str(len(rows)),
                "long_rows": str(long_by_year[year]),
                "unique_harvest_hunt_codes": str(len(year_codes)),
                "current_database_hunt_codes": str(len(current_codes)),
                "current_database_codes_covered": str(len(current_covered)),
                "current_database_codes_missing": str(len(current_missing)),
                "current_database_coverage_pct": f"{(len(current_covered) / len(current_codes) * 100):.2f}",
                "historical_only_harvest_codes": str(len(year_codes - current_codes)),
                "guardrail_rows": str(guardrail_rows),
                "metric_issue_rows": str(issues_by_year[year]),
                "success_rate_math_conflicts": str(success_conflicts_by_year[year]),
                "source_status_counts": pipe_counter(source_status),
                "parse_status_counts": pipe_counter(parse_status),
                "species_counts": pipe_counter(species_counts),
                **numeric_counts,
            }
        )

        for code in sorted(current_missing):
            db_row = current_by_code[code]
            covered_any_year = code in current_codes_covered_any_year
            missing_rows.append(
                {
                    "reported_hunt_year": year,
                    "expected_model_target_year": str(int(year) + 1) if year.isdigit() else "",
                    "hunt_code": code,
                    "boundary_id": db_row.get("boundary_id", ""),
                    "species": db_row.get("species", ""),
                    "sex_type": db_row.get("sex_type", ""),
                    "hunt_name": db_row.get("hunt_name", ""),
                    "hunt_type": db_row.get("hunt_type", ""),
                    "hunt_class": db_row.get("hunt_class", ""),
                    "weapon": db_row.get("weapon", ""),
                    "covered_in_any_harvest_year": "YES" if covered_any_year else "NO",
                    "missing_reason": classify_missing(db_row, covered_any_year),
                }
            )

    historical_rows = []
    for code in historical_only_codes:
        code_rows = [row for row in best_rows if norm(row.get("hunt_code")) == code]
        historical_rows.append(
            {
                "hunt_code": code,
                "reported_hunt_years": "|".join(sorted({norm(row.get("reported_hunt_year")) for row in code_rows})),
                "species_values": "|".join(sorted({norm(row.get("species")) for row in code_rows if norm(row.get("species"))})),
                "hunt_name_values": "|".join(sorted({norm(row.get("hunt_name")) for row in code_rows if norm(row.get("hunt_name"))}))[:600],
                "row_count": str(len(code_rows)),
                "review_status": "HISTORICAL_CODE_NOT_IN_CURRENT_DATABASE",
            }
        )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "audit_scope": "read_only_harvest_truth_year_by_year_hardening",
        "database_path": str(DATABASE.relative_to(ROOT)),
        "harvest_best_path": str(BEST.relative_to(ROOT)),
        "harvest_long_path": str(LONG.relative_to(ROOT)),
        "current_database_rows": len(database_rows),
        "current_database_unique_hunt_codes": len(current_codes),
        "harvest_best_rows": len(best_rows),
        "harvest_long_rows": len(long_rows),
        "unique_reported_hunt_years": years,
        "unique_harvest_hunt_codes_all_years": len(harvest_codes_all_years),
        "current_database_codes_covered_any_harvest_year": len(current_codes_covered_any_year),
        "current_database_codes_missing_all_harvest_years": len(current_codes - current_codes_covered_any_year),
        "historical_only_harvest_codes_not_current_database": len(historical_only_codes),
        "year_rows": year_rows,
        "missing_code_rows": len(missing_rows),
        "blocker_count": 0,
        "guardrails": [
            "Read-only audit: no harvest truth rows, DATABASE.csv values, website feeds, or draw prediction files are modified.",
            "Harvest permit values remain harvest-report context only and must not be promoted to current-year draw allotments.",
            "Reported hunt year remains the completed harvest year; model target year is reported_hunt_year + 1.",
        ],
        "outputs": {
            "year_coverage_csv": str(YEAR_CSV.relative_to(ROOT)),
            "missing_codes_csv": str(MISSING_CSV.relative_to(ROOT)),
            "historical_only_codes_csv": str(HISTORICAL_ONLY_CSV.relative_to(ROOT)),
            "summary_json": str(SUMMARY_JSON.relative_to(ROOT)),
            "summary_md": str(REPORT_MD.relative_to(ROOT)),
        },
    }

    year_fields = list(year_rows[0].keys()) if year_rows else []
    missing_fields = [
        "reported_hunt_year",
        "expected_model_target_year",
        "hunt_code",
        "boundary_id",
        "species",
        "sex_type",
        "hunt_name",
        "hunt_type",
        "hunt_class",
        "weapon",
        "covered_in_any_harvest_year",
        "missing_reason",
    ]
    historical_fields = [
        "hunt_code",
        "reported_hunt_years",
        "species_values",
        "hunt_name_values",
        "row_count",
        "review_status",
    ]
    write_rows(YEAR_CSV, year_rows, year_fields)
    write_rows(MISSING_CSV, missing_rows, missing_fields)
    write_rows(HISTORICAL_ONLY_CSV, historical_rows, historical_fields)
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(build_markdown(summary), encoding="utf-8")

    print(
        "Harvest hardening audit complete: "
        f"{len(current_codes_covered_any_year)}/{len(current_codes)} current codes covered in at least one harvest year; "
        f"{len(current_codes - current_codes_covered_any_year)} need all-year review."
    )
    return 0


def build_markdown(summary: dict[str, object]) -> str:
    year_rows = summary["year_rows"]
    lines = [
        "# Harvest Year-By-Year Hardening Audit 2026",
        "",
        "Read-only audit of normalized harvest truth against the current 2026 canonical hunt-code universe.",
        "",
        "## Topline",
        "",
        f"- Current DATABASE hunt codes: {summary['current_database_unique_hunt_codes']}",
        f"- Harvest best rows: {summary['harvest_best_rows']}",
        f"- Harvest long rows: {summary['harvest_long_rows']}",
        f"- Current codes covered in at least one harvest year: {summary['current_database_codes_covered_any_harvest_year']}",
        f"- Current codes missing from all harvest years: {summary['current_database_codes_missing_all_harvest_years']}",
        f"- Historical harvest codes not in current DATABASE: {summary['historical_only_harvest_codes_not_current_database']}",
        "",
        "## Year Coverage",
        "",
        "| Reported hunt year | Best rows | Current codes covered | Current codes missing | Coverage | Metric warnings |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in year_rows:
        lines.append(
            "| {year} | {best} | {covered} | {missing} | {pct}% | {warnings} |".format(
                year=row["reported_hunt_year"],
                best=row["best_rows"],
                covered=row["current_database_codes_covered"],
                missing=row["current_database_codes_missing"],
                pct=row["current_database_coverage_pct"],
                warnings=row["metric_issue_rows"],
            )
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- This audit does not change harvest truth rows, `DATABASE.csv`, website feeds, or draw predictions.",
            "- Missing rows are repair targets, not proof that a hunt lacked harvest.",
            "- Harvest `permits` fields remain report-context values and are not draw allotments.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
