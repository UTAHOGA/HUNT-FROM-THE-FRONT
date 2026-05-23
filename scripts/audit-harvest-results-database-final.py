"""Final structural audit for the all-years harvest-result database.

This script validates harvest data as quality/history input only. It does not
extract PDFs, rebuild packages, or modify draw probability/quota files.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.utah.quality.harvest_feature_model import clean_numeric, success_rate_check
from engine.utah.quality.materialize_harvest_feature_model import FEATURE_FIELDS, build_feature_row


PROCESSED = ROOT / "processed_data"

FILES_TO_AUDIT = [
    ROOT / "data_truth" / "harvest_results_truth" / "normalized" / "harvest_results_all_years_long.csv",
    ROOT / "data_truth" / "harvest_results_truth" / "normalized" / "harvest_quality_features_all_years_by_hunt_code.csv",
    ROOT / "data_model" / "harvest_quality" / "harvest_results_all_years_long.csv",
    ROOT / "data_model" / "harvest_quality" / "harvest_quality_features_all_years_by_hunt_code.csv",
    PROCESSED / "harvest_results_all_years_long.csv",
    PROCESSED / "harvest_quality_features_all_years_by_hunt_code.csv",
    PROCESSED / "special_permit_overlay_classes_all_years.csv",
]

LONG = ROOT / "data_truth" / "harvest_results_truth" / "normalized" / "harvest_results_all_years_long.csv"
BEST = ROOT / "data_truth" / "harvest_results_truth" / "normalized" / "harvest_quality_features_all_years_by_hunt_code.csv"
SOURCE_AUDIT = ROOT / "data_truth" / "harvest_results_truth" / "normalized" / "harvest_results_all_years_source_audit.csv"
SUMMARY = ROOT / "data_truth" / "harvest_results_truth" / "normalized" / "harvest_results_all_years_summary.json"
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
OVERLAY = PROCESSED / "special_permit_overlay_classes_all_years.csv"

REQUIRED_FIELDS = [
    "reported_hunt_year",
    "model_target_year",
    "hunt_code",
    "species",
    "hunt_name",
    "source_family",
    "source_file",
    "source_status",
    "permits",
    "hunters_afield",
    "harvest",
    "average_days",
    "percent_success",
    "hunter_satisfaction",
    "do_not_use_for_permit_quota",
    "do_not_use_directly_for_p_draw",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        text = str(row.get(key, "") or "").strip()
        if text:
            return text
    return ""


def source_family(row: dict[str, str]) -> str:
    return value(row, "source_family", "source_kind", "hunt_type", "permit_overlay_class")


def harvest_value(row: dict[str, str]) -> str:
    return value(row, "harvest", "harvest_total", "male_harvest", "female_harvest")


def source_inventory() -> list[dict[str, str]]:
    rows = []
    for path in FILES_TO_AUDIT:
        data = read_rows(path)
        fields = list(data[0].keys()) if data else []
        unique_codes = {row.get("hunt_code", "").strip() for row in data if row.get("hunt_code", "").strip()}
        row_tuples = [tuple((field, row.get(field, "")) for field in fields) for row in data]
        rows.append(
            {
                "file": rel(path),
                "exists": str(path.exists()),
                "row_count": str(len(data)),
                "column_count": str(len(fields)),
                "unique_hunt_code_count": str(len(unique_codes)),
                "reported_hunt_year_coverage": "|".join(sorted({row.get("reported_hunt_year", "") for row in data if row.get("reported_hunt_year")})),
                "model_target_year_coverage": "|".join(sorted({row.get("model_target_year", "") for row in data if row.get("model_target_year")})),
                "species_coverage": "|".join(sorted({row.get("species", "") for row in data if row.get("species")})),
                "source_family_coverage": "|".join(sorted({source_family(row) for row in data if source_family(row)})),
                "duplicate_row_count": str(len(row_tuples) - len(set(row_tuples))),
                "blank_hunt_code_count": str(sum(1 for row in data if not row.get("hunt_code", "").strip())),
                "blank_species_count": str(sum(1 for row in data if not row.get("species", "").strip())),
                "blank_reported_hunt_year_count": str(sum(1 for row in data if not row.get("reported_hunt_year", "").strip())),
            }
        )
    return rows


def missing_reason(row: dict[str, str], field: str) -> str:
    text = " ".join([source_family(row), row.get("source_file", ""), row.get("source_container", ""), row.get("hunt_name", "")]).lower()
    if "overlay" in text or "cwmu" in text or "expo" in text or "conservation" in text or "sportsman" in text:
        return "SPECIAL_PERMIT_OVERLAY_ROW"
    if "statewide" in text:
        return "STATEWIDE_HISTORY_ROW"
    if "trend" in text:
        return "NON_HARVEST_TREND_TABLE"
    if "measurement" in text or "age" in text:
        return "INDIVIDUAL_MEASUREMENT_ROW"
    if field in {"hunter_satisfaction", "average_days", "source_status"}:
        return "SOURCE_DOES_NOT_REPORT_FIELD"
    return "PARSE_GAP_NEEDS_REVIEW"


def required_field_audit(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    output = []
    for field in REQUIRED_FIELDS:
        missing = 0
        reasons: Counter[str] = Counter()
        for row in rows:
            field_value = ""
            if field == "source_family":
                field_value = source_family(row)
            elif field == "harvest":
                field_value = harvest_value(row)
            else:
                field_value = row.get(field, "")
            if not str(field_value or "").strip():
                missing += 1
                reasons[missing_reason(row, field)] += 1
        output.append(
            {
                "audit_type": "required_field",
                "field": field,
                "row_count": str(len(rows)),
                "missing_count": str(missing),
                "present_count": str(len(rows) - missing),
                "missingness_reason_counts": json.dumps(dict(reasons), sort_keys=True),
                "severity": "WARNING" if missing else "PASS",
            }
        )
    return output


def duplicate_audit(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    key_specs = {
        "source_file+source_row_id": lambda r, i: (r.get("source_file", ""), r.get("source_row_id", str(i))),
        "reported_hunt_year+hunt_code+source_family": lambda r, i: (r.get("reported_hunt_year", ""), r.get("hunt_code", ""), source_family(r)),
        "reported_hunt_year+hunt_code+species": lambda r, i: (r.get("reported_hunt_year", ""), r.get("hunt_code", ""), r.get("species", "")),
        "reported_hunt_year+hunt_code+species+hunt_name": lambda r, i: (
            r.get("reported_hunt_year", ""),
            r.get("hunt_code", ""),
            r.get("species", ""),
            r.get("hunt_name", ""),
        ),
        "model_target_year+hunt_code+species": lambda r, i: (r.get("model_target_year", ""), r.get("hunt_code", ""), r.get("species", "")),
    }
    output = []
    for key_name, key_func in key_specs.items():
        grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
        for index, row in enumerate(rows):
            key = tuple(key_func(row, index))
            if any(key):
                grouped[key].append(row)
        for key, group in grouped.items():
            if len(group) <= 1:
                continue
            families = {source_family(row) for row in group}
            containers = {row.get("source_container", "") for row in group}
            if any("overlay" in fam.lower() or fam in {"CWMU", "EXPO", "CONSERVATION", "SPORTSMAN"} for fam in families):
                classification = "SPECIAL_PERMIT_OVERLAY_DUPLICATE_ALLOWED"
            elif len(containers) > 1:
                classification = "SAME_HUNT_DIFFERENT_SOURCE"
            elif any("supplement" in row.get("source_container", "").lower() for row in group):
                classification = "SUPPLEMENTAL_QUALITY_ROW"
            else:
                classification = "NEEDS_REVIEW"
            output.append(
                {
                    "key_level": key_name,
                    "key": "|".join(key),
                    "duplicate_count": str(len(group)),
                    "classification": classification,
                    "severity": "WARNING" if classification == "NEEDS_REVIEW" else "INFO",
                    "source_families": "|".join(sorted(families)),
                    "source_containers": "|".join(sorted(containers))[:500],
                }
            )
    return output


def metric_integrity_audit(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    output = []
    for index, row in enumerate(rows, start=1):
        family = source_family(row)
        harvest = clean_numeric(harvest_value(row))
        hunters = clean_numeric(row.get("hunters_afield"))
        permits = clean_numeric(row.get("permits"))
        success = clean_numeric(row.get("percent_success"))
        avg_days = clean_numeric(row.get("average_days"))
        satisfaction = clean_numeric(row.get("hunter_satisfaction"))
        flags = []
        if harvest is not None and hunters is not None and harvest > hunters and "statewide" not in family.lower():
            flags.append("HARVEST_GREATER_THAN_HUNTERS")
        if hunters is not None and permits is not None and hunters > permits and "statewide" not in family.lower():
            flags.append("HUNTERS_GREATER_THAN_PERMITS_REVIEW")
        if any(value is not None and value < 0 for value in [harvest, hunters, permits, avg_days]):
            flags.append("NEGATIVE_METRIC")
        if success is not None and not (0 <= success <= 100):
            flags.append("IMPOSSIBLE_PERCENT")
        if satisfaction is not None and not (0 <= satisfaction <= 10):
            flags.append("PLAUSIBLE_BUT_REVIEW")
        check = success_rate_check({"harvest_total": harvest, "hunters_afield": hunters, "percent_success": success})
        if check["status"] == "CONFLICT":
            flags.append("SUCCESS_RATE_MATH_CONFLICT")
        if not flags:
            continue
        output.append(
            {
                "row_number": str(index),
                "hunt_code": row.get("hunt_code", ""),
                "reported_hunt_year": row.get("reported_hunt_year", ""),
                "species": row.get("species", ""),
                "source_family": family,
                "source_file": row.get("source_file", ""),
                "flags": "|".join(sorted(set(flags))),
                "severity": "WARNING",
                "harvest": "" if harvest is None else str(harvest),
                "hunters_afield": "" if hunters is None else str(hunters),
                "permits": "" if permits is None else str(permits),
                "percent_success": "" if success is None else str(success),
                "expected_success_pct": "" if check.get("expected_success_pct") is None else f"{check['expected_success_pct']:.3f}",
            }
        )
    return output


def year_coverage_audit(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    output = []
    years = {row.get("reported_hunt_year", "") for row in rows if row.get("reported_hunt_year")}
    model_years = {row.get("model_target_year", "") for row in rows if row.get("model_target_year")}
    for year in ["2021", "2022", "2023", "2024", "2025"]:
        output.append({"check": f"reported_hunt_year_{year}", "status": "COMPLETE" if year in years else "NEEDS_REVIEW", "details": ""})
    for year in ["2022", "2023", "2024", "2025", "2026"]:
        output.append({"check": f"model_target_year_{year}", "status": "COMPLETE" if year in model_years else "NEEDS_REVIEW", "details": ""})
    text = "\n".join(row.get("source_container", "") + " " + row.get("source_file", "") for row in rows).lower()
    expected = {
        "turkey_2023_24": "turkey_harvest_results_2023_24",
        "turkey_2024_25": "turkey_harvest_results_2024_25",
        "black_bear_2024_supplement": "black_bear_supplement",
        "elk_average_age_2024_supplement": "elk_age_supplement",
        "oil_bison_sheep_goat_supplement": "extra_oil_supplement",
        "preliminary_2025_harvest": "2025_for_2026",
    }
    for check, needle in expected.items():
        status = "PRELIMINARY_SOURCE_ONLY" if check == "preliminary_2025_harvest" and needle in text else ("COMPLETE" if needle in text else "NEEDS_REVIEW")
        output.append({"check": check, "status": status, "details": needle})
    by_species_year: Counter[tuple[str, str]] = Counter((row.get("species", ""), row.get("reported_hunt_year", "")) for row in rows)
    for (species, year), count in sorted(by_species_year.items()):
        if species and year:
            output.append({"check": f"species_year:{species}:{year}", "status": "COMPLETE", "details": str(count)})
    return output


def hunt_code_alignment_audit(rows: list[dict[str, str]], db_rows: list[dict[str, str]], overlay_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    db_by_code = {row["hunt_code"]: row for row in db_rows if row.get("hunt_code")}
    overlay_codes = {row.get("hunt_code", "") for row in overlay_rows}
    harvest_codes = sorted({row.get("hunt_code", "") for row in rows if row.get("hunt_code")})
    output = []
    for code in harvest_codes:
        code_rows = [row for row in rows if row.get("hunt_code") == code]
        sample = code_rows[-1]
        if code in db_by_code and code in overlay_codes:
            classification = "SPECIAL_PERMIT_OVERLAY"
        elif code in db_by_code:
            classification = "ACTIVE_2026_DATABASE_CODE"
        elif code in overlay_codes:
            classification = "SPECIAL_PERMIT_OVERLAY"
        elif code.upper().startswith("STATEWIDE"):
            classification = "STATEWIDE_HISTORY_ONLY"
        else:
            classification = "HARVEST_ONLY_CODE"
        output.append(
            {
                "hunt_code": code,
                "hunt_name": sample.get("hunt_name", ""),
                "species": sample.get("species", ""),
                "reported_hunt_years": "|".join(sorted({row.get("reported_hunt_year", "") for row in code_rows if row.get("reported_hunt_year")})),
                "classification": classification,
                "active_2026_database": "YES" if code in db_by_code else "NO",
                "row_count": str(len(code_rows)),
            }
        )
    for code, row in db_by_code.items():
        if code not in harvest_codes:
            output.append(
                {
                    "hunt_code": code,
                    "hunt_name": row.get("hunt_name", ""),
                    "species": row.get("species", ""),
                    "reported_hunt_years": "",
                    "classification": "NEW_2026_NO_PRIOR_HARVEST",
                    "active_2026_database": "YES",
                    "row_count": "0",
                }
            )
    return output


def feature_readiness_audit(db_rows: list[dict[str, str]], history_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for db_row in db_rows:
        if not db_row.get("hunt_code"):
            continue
        feature = build_feature_row(db_row, history_rows, 2026)
        output = {
            "hunt_code": db_row.get("hunt_code", ""),
            "species": db_row.get("species", ""),
            "hunt_name": db_row.get("hunt_name", ""),
            "active_2026": "YES",
            "best_harvest_match_method": feature.get("harvest_feature_match_method", ""),
        }
        for field in FEATURE_FIELDS:
            output[field] = feature.get(field, "")
        rows.append(output)
    return rows


def write_contract(path: Path) -> None:
    text = """# Harvest Results Database Modeling Contract

Harvest data is a quality, demand-signal, effort, trend, and explanatory metadata source. It is not a public draw-odds source and it is not a current-year quota/allotment source.

## Harvest Data May Model
- applicant demand pressure
- hunt quality trend
- hunter effort trend
- hunter satisfaction trend
- trophy/age trend
- sex-structure trend
- population/trend-count signal
- pursuit pressure signal
- fallback quality features for new or renamed hunt codes
- calibration and explanatory metadata

## Harvest Data May Not Model Directly
- public draw odds
- p_draw
- p_random_mean
- p_max_pool_mean
- p_preference_draw
- p_bonus_pool
- 2026 official quota
- 2026 public draw permit allotment
- max-point pool permit count
- random-pool permit count

Harvest report permit counts remain historical harvest-report context. They must not overwrite `permits_2026_*`, `permit_allotment_2026_*`, `quota_2026_*`, or any active public draw allotment field.

Expo, Conservation, Sportsman, and CWMU permit overlays are retained for total-permit reconciliation and audit traceability only. They must not be merged into public draw odds or `p_draw` math.

Any feature materialization that joins harvest features onto predictive rows must assert that probability fields and 2026 quota/allotment fields are unchanged before and after the join.
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    long_rows = read_rows(LONG)
    best_rows = read_rows(BEST)
    source_rows = read_rows(SOURCE_AUDIT)
    db_rows = read_rows(DATABASE)
    overlay_rows = read_rows(OVERLAY)

    inventory = source_inventory()
    required = required_field_audit(long_rows)
    key_integrity = duplicate_audit(best_rows)
    metric = metric_integrity_audit(long_rows)
    year_coverage = year_coverage_audit(best_rows)
    alignment = hunt_code_alignment_audit(best_rows, db_rows, overlay_rows)
    readiness = feature_readiness_audit(db_rows, best_rows)
    write_contract(PROCESSED / "harvest_results_database_modeling_contract.md")

    write_rows(PROCESSED / "harvest_results_database_final_audit.csv", inventory + required, sorted(set((inventory + required)[0].keys()) | set(required[0].keys())))
    write_rows(PROCESSED / "harvest_results_database_key_integrity_audit.csv", key_integrity, list(key_integrity[0].keys()) if key_integrity else ["key_level"])
    write_rows(PROCESSED / "harvest_results_database_metric_integrity_audit.csv", metric, list(metric[0].keys()) if metric else ["row_number"])
    write_rows(PROCESSED / "harvest_results_database_year_coverage_audit.csv", year_coverage, ["check", "status", "details"])
    write_rows(PROCESSED / "harvest_results_database_hunt_code_alignment_audit.csv", alignment, list(alignment[0].keys()) if alignment else ["hunt_code"])
    readiness_fields = [
        "hunt_code",
        "species",
        "hunt_name",
        "active_2026",
        "best_harvest_match_method",
    ] + FEATURE_FIELDS
    write_rows(PROCESSED / "harvest_results_database_feature_readiness_audit.csv", readiness, readiness_fields)

    warning_count = len(metric) + sum(1 for row in key_integrity if row.get("severity") == "WARNING") + sum(1 for row in required if row.get("severity") == "WARNING")
    blocker_count = sum(1 for row in key_integrity if row.get("classification") == "TRUE_DUPLICATE_BLOCKER")
    summary = json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else {}
    final = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "harvest_database_row_count": len(long_rows),
        "best_by_year_hunt_code_row_count": len(best_rows),
        "source_audit_row_count": len(source_rows),
        "reported_hunt_year_coverage": sorted({row.get("reported_hunt_year", "") for row in best_rows if row.get("reported_hunt_year")}),
        "model_target_year_coverage": sorted({row.get("model_target_year", "") for row in best_rows if row.get("model_target_year")}),
        "exact_hunt_code_feature_matches": sum(1 for row in readiness if row["best_harvest_match_method"] == "EXACT_HUNT_CODE_HISTORY"),
        "fallback_feature_matches": sum(1 for row in readiness if row["best_harvest_match_method"] not in {"EXACT_HUNT_CODE_HISTORY", "NO_HARVEST_HISTORY"}),
        "no_history_rows": sum(1 for row in readiness if row["best_harvest_match_method"] == "NO_HARVEST_HISTORY"),
        "audit_blocker_count": blocker_count,
        "audit_warning_count": warning_count,
        "metric_issue_count": len(metric),
        "success_rate_math_conflict_count": sum(1 for row in metric if "SUCCESS_RATE_MATH_CONFLICT" in row.get("flags", "")),
        "key_integrity_issue_count": len(key_integrity),
        "feature_readiness_rows": len(readiness),
        "harvest_quality_index_count": sum(1 for row in readiness if row.get("harvest_quality_index")),
        "demand_pressure_signal_count": sum(1 for row in readiness if row.get("demand_pressure_signal")),
        "summary_source": summary,
        "outputs": {
            "final_audit_csv": "processed_data/harvest_results_database_final_audit.csv",
            "key_integrity_csv": "processed_data/harvest_results_database_key_integrity_audit.csv",
            "metric_integrity_csv": "processed_data/harvest_results_database_metric_integrity_audit.csv",
            "year_coverage_csv": "processed_data/harvest_results_database_year_coverage_audit.csv",
            "hunt_code_alignment_csv": "processed_data/harvest_results_database_hunt_code_alignment_audit.csv",
            "feature_readiness_csv": "processed_data/harvest_results_database_feature_readiness_audit.csv",
            "modeling_contract_md": "processed_data/harvest_results_database_modeling_contract.md",
        },
    }
    (PROCESSED / "harvest_results_database_final_audit.json").write_text(json.dumps(final, indent=2), encoding="utf-8")
    md = [
        "# Harvest Results Database Final Audit",
        "",
        f"- harvest_database_row_count: {final['harvest_database_row_count']}",
        f"- best_by_year_hunt_code_row_count: {final['best_by_year_hunt_code_row_count']}",
        f"- reported_hunt_year_coverage: {final['reported_hunt_year_coverage']}",
        f"- model_target_year_coverage: {final['model_target_year_coverage']}",
        f"- exact_hunt_code_feature_matches: {final['exact_hunt_code_feature_matches']}",
        f"- fallback_feature_matches: {final['fallback_feature_matches']}",
        f"- no_history_rows: {final['no_history_rows']}",
        f"- audit_blocker_count: {final['audit_blocker_count']}",
        f"- audit_warning_count: {final['audit_warning_count']}",
        f"- success_rate_math_conflict_count: {final['success_rate_math_conflict_count']}",
        "",
        "Harvest data remains quality/demand-signal only. It must not overwrite draw odds, probability fields, or 2026 quota/allotment fields.",
    ]
    (PROCESSED / "harvest_results_database_final_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(final, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
