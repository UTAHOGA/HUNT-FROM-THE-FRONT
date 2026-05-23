"""Build a final publish-readiness report for the 2026 hunt database.

This report cross-checks promoted source data, canonical DATABASE.csv, runtime
feed surfaces, prediction guardrails, and catalog display semantics. It does not
change model math or mutate data.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "processed_data"
OUT_JSON = PROCESSED / "database_publish_readiness_report.json"
OUT_MD = PROCESSED / "database_publish_readiness_report.md"

OLD_DRAW_FAMILY_LABELS = {"BONUS", "ANTLERLESS", "TURKEY_DRAW", "NONE", "HARVEST_OBJECTIVE", "UNKNOWN"}
PROBABILITY_FIELDS = ["p_draw", "p_draw_pct", "p_preference_draw", "p_bonus_pool", "p_random_pool"]
NULL_PROBABILITY_STATUSES = {
    "MODELED_AVAILABILITY",
    "MODELED_ALLOCATION",
    "IN_SCOPE_MODEL_PENDING",
    "EXCLUDED_NOT_PREDICTIVE_DRAW",
    "OUT_OF_SCOPE_NON_TARGET",
}


def read_json(rel: str, default: Any = None) -> Any:
    path = ROOT / rel
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(rel: str) -> list[dict[str, str]]:
    path = ROOT / rel
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def non_null(value: object) -> bool:
    text = clean(value)
    return text not in {"", "null", "None", "nan", "NaN"}


def row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (clean(row.get("hunt_code")).upper(), clean(row.get("residency")), clean(row.get("points")))


def duplicate_key_count(rows: list[dict[str, str]]) -> int:
    counts = Counter(row_key(row) for row in rows if clean(row.get("hunt_code")))
    return sum(1 for count in counts.values() if count > 1)


def by_code(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        code = clean(row.get("hunt_code") or row.get("huntCode") or row.get("code")).upper()
        if code:
            out.setdefault(code, []).append(row)
    return out


def pick(rows: list[dict[str, str]], *, residency: str | None = None, points: str | None = None) -> dict[str, str]:
    for row in rows:
        if residency is not None and clean(row.get("residency")) != residency:
            continue
        if points is not None and clean(row.get("points")) != points:
            continue
        return row
    return rows[0] if rows else {}


def count_probability_violations(rows: list[dict[str, str]]) -> dict[str, Any]:
    status_counts = Counter(clean(row.get("algorithm_status")) for row in rows)
    violations: list[dict[str, str]] = []
    for row in rows:
        status = clean(row.get("algorithm_status"))
        if status not in NULL_PROBABILITY_STATUSES:
            continue
        for field in PROBABILITY_FIELDS:
            if non_null(row.get(field)):
                violations.append(
                    {
                        "hunt_code": clean(row.get("hunt_code")),
                        "residency": clean(row.get("residency")),
                        "points": clean(row.get("points")),
                        "algorithm_status": status,
                        "field": field,
                        "value": clean(row.get(field)),
                    }
                )
    return {
        "algorithm_status_counts": dict(sorted(status_counts.items())),
        "null_probability_violation_count": len(violations),
        "null_probability_violation_examples": violations[:50],
        "pending_rows_with_p_draw": sum(
            1
            for row in rows
            if clean(row.get("algorithm_status")) == "IN_SCOPE_MODEL_PENDING" and non_null(row.get("p_draw"))
        ),
        "out_of_scope_rows_with_p_draw": sum(
            1
            for row in rows
            if clean(row.get("algorithm_status")) == "OUT_OF_SCOPE_NON_TARGET" and non_null(row.get("p_draw"))
        ),
        "excluded_rows_with_p_draw": sum(
            1
            for row in rows
            if clean(row.get("algorithm_status")) == "EXCLUDED_NOT_PREDICTIVE_DRAW" and non_null(row.get("p_draw"))
        ),
        "availability_rows_with_p_draw": sum(
            1
            for row in rows
            if clean(row.get("algorithm_status")) == "MODELED_AVAILABILITY" and non_null(row.get("p_draw"))
        ),
    }


def draw_family_check() -> dict[str, Any]:
    files = [
        "data/hunt-master-canonical-2026-database-candidate.csv",
        "data/hunt-master-canonical-2026-source-of-truth.csv",
        "canonical/hunt-planner-2026.json",
        "generated/pages/hunt-planner.json",
        "hunt-master-canonical-2026.json",
    ]
    details = []
    old_hits: list[dict[str, str]] = []
    for rel in files:
        path = ROOT / rel
        if not path.exists():
            details.append({"file": rel, "exists": False})
            continue
        if path.suffix == ".csv":
            rows = read_csv(rel)
        else:
            data = read_json(rel, {})
            rows = data if isinstance(data, list) else data.get("hunt_catalog", [])
        counts = Counter(clean(row.get("draw_family")) for row in rows if isinstance(row, dict))
        for label in OLD_DRAW_FAMILY_LABELS:
            if counts.get(label):
                old_hits.append({"file": rel, "label": label, "count": str(counts[label])})
        details.append({"file": rel, "exists": True, "rows": len(rows), "counts": dict(sorted(counts.items()))})
    return {
        "old_internal_label_hit_count": len(old_hits),
        "old_internal_label_hits": old_hits,
        "files": details,
    }


def sensitive_row_checks() -> dict[str, Any]:
    database = by_code(read_csv("pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"))
    reference = by_code(read_csv("processed_data/hunt_unit_reference_linked.csv"))
    ml = by_code(read_csv("processed_data/ml_draw_predictions_v1.csv"))
    ladder = by_code(read_csv("processed_data/point_ladder_view.csv"))

    checks: dict[str, Any] = {}

    def expect(label: str, actual: object, expected: object) -> None:
        checks[label] = {
            "actual": actual,
            "expected": expected,
            "pass": actual == expected,
        }

    ea1267 = pick(database.get("EA1267", []))
    expect("EA1267_DATABASE_2026_TOTAL", clean(ea1267.get("permits_2026_total")), "200")
    expect("EA1267_DATABASE_2026_RES", clean(ea1267.get("permits_2026_res")), "180")
    expect("EA1267_DATABASE_2026_NR", clean(ea1267.get("permits_2026_nr")), "20")

    ea2012_ref = pick(reference.get("EA2012", []))
    expect("EA2012_REFERENCE_TOTAL_ONLY_TOTAL", clean(ea2012_ref.get("permit_allotment_2026_total")), "500")
    expect("EA2012_REFERENCE_NO_RES_SPLIT", clean(ea2012_ref.get("permit_allotment_2026_res")), "")
    expect("EA2012_REFERENCE_PUBLIC_PERMITS_BLANK", clean(ea2012_ref.get("public_permits_2026")), "")
    expect("EA2012_REFERENCE_PROBABILITY_MODEL_NONE", clean(ea2012_ref.get("probability_model")), "NONE")

    pd1039 = pick(database.get("PD1039", []))
    expect("PD1039_ADDED_TO_DATABASE", bool(pd1039), True)
    expect("PD1039_DATABASE_2026_TOTAL", clean(pd1039.get("permits_2026_total")), "40")

    eb3024 = pick(ml.get("EB3024", []), residency="Resident", points="29")
    expect("EB3024_RESIDENT_POINT_29_QUOTA_TOTAL", clean(eb3024.get("quota_2026_total")), "9")
    expect("EB3024_RESIDENT_POINT_29_MAX_POOL", clean(eb3024.get("quota_2026_max_pool")), "5")
    expect("EB3024_RESIDENT_POINT_29_RANDOM_POOL", clean(eb3024.get("quota_2026_random_pool")), "4")
    checks["EB3024_RESIDENT_RAC_REASON_CODE"] = {
        "actual": clean(eb3024.get("reason_codes")),
        "expected_contains": "RAC_CURRENT_YEAR_ALLOTMENT_USED",
        "pass": "RAC_CURRENT_YEAR_ALLOTMENT_USED" in clean(eb3024.get("reason_codes")),
    }

    eb3022 = pick(ml.get("EB3022", []), residency="Resident", points="7")
    expect("EB3022_RESIDENT_QUOTA_TOTAL", clean(eb3022.get("quota_2026_total")), "130")
    expect("EB3022_RESIDENT_MAX_POOL", clean(eb3022.get("quota_2026_max_pool")), "65")
    expect("EB3022_RESIDENT_RANDOM_POOL", clean(eb3022.get("quota_2026_random_pool")), "65")

    br1000 = pick(database.get("BR1000", []))
    expect("BR1000_DATABASE_HUNT_TYPE", clean(br1000.get("hunt_type")), "Statewide")

    br1001 = pick(ml.get("BR1001", []), residency="Resident")
    expect("BR1001_P_DRAW_NULL", clean(br1001.get("p_draw")), "")
    expect("BR1001_ALGORITHM_STATUS", clean(br1001.get("algorithm_status")), "MODELED_AVAILABILITY")

    ladder_eb3024_29 = pick(ladder.get("EB3024", []), residency="Resident", points="29")
    expect("EB3024_LADDER_29_MAX_POINT_DISPLAY", clean(ladder_eb3024_29.get("display_2026_max_point_pool")), "~1 in 7 or 14.3%")
    ladder_eb3024_28 = pick(ladder.get("EB3024", []), residency="Resident", points="28")
    expect("EB3024_LADDER_28_MAX_POINT_BLANK", clean(ladder_eb3024_28.get("display_2026_max_point_pool")), "")

    failed = {key: value for key, value in checks.items() if not value["pass"]}
    return {"checks": checks, "failed_count": len(failed), "failed": failed}


def command_inventory() -> list[str]:
    return [
        "python scripts/build-all-rac-permit-database-compare.py",
        "python scripts/compare-antlerless-elk-allotments.py",
        "python -m engine.utah.truth_source_promotion --truth-root pipeline/RAW/hunt_unit_database/2026/csv --processed-root processed_data --families doe_pronghorn antlerless_deer standard_antlerless_elk private_lands_antlerless_elk antlerless_elk_control_units antlerless_moose ewe_rocky_sheep --promote --write-audits",
        "python -m engine.utah_draw_predictive.availability_review --output-dir processed_data --forecast-year 2026 --history-years 2021,2022,2023,2024,2025",
        "npm.cmd run verify:permits-2026",
        "python -m pytest tests/utah/test_draw_family_labels.py tests/utah/test_current_year_permit_allotments.py tests/utah/test_truth_source_promotion.py tests/utah_bonus_predictive/test_official_2026_quota_inputs.py tests/utah/test_point_ladder_pool_display.py -q",
        "python -m pytest -q tests/utah_draw_predictive tests/utah/test_frontend_probability_selection.py",
        "python -m pytest -q tests/utah_bonus_predictive",
        "python -m compileall engine scripts tests",
        "node --check hunt-research.js",
        "node --check scripts/verify-permit-allocations-2026.js",
        "npm.cmd test",
    ]


def build_report() -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    database_rows = read_csv("pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv")
    database_codes = {clean(row.get("hunt_code")).upper() for row in database_rows if clean(row.get("hunt_code"))}
    database_duplicate_codes = [code for code, count in Counter(clean(row.get("hunt_code")).upper() for row in database_rows if clean(row.get("hunt_code"))).items() if count > 1]

    rac = read_json("processed_data/all_rac_2026_permits_vs_DATABASE.json", {})
    truth = read_json("processed_data/truth_source_promotion_summary.json", {})
    permits = read_json("canonical/permit-allocation-2026-integrity-report.json", {})
    antlerless_elk = read_json("processed_data/antlerless_elk_current_rac_allotment_vs_database_runtime.json", {}).get("summary", {})
    coverage = read_json("processed_data/draw_system_coverage_report.json", {})
    gpt = read_json("processed_data/gpt_work_review_report.json", {})
    availability = read_json("processed_data/modeled_availability_review_report.json", {})

    if database_duplicate_codes:
        blockers.append(f"DATABASE.csv duplicate hunt codes: {len(database_duplicate_codes)}")

    source_to_database = {
        "database_rows": len(database_rows),
        "database_unique_hunt_codes": len(database_codes),
        "database_duplicate_hunt_code_count": len(database_duplicate_codes),
        "rac_cumulative_rows": rac.get("cumulative_rac_rows"),
        "rac_hunt_code_rows": rac.get("cumulative_rac_hunt_code_rows"),
        "rac_unique_hunt_codes": rac.get("cumulative_rac_unique_hunt_codes"),
        "rac_hunt_codes_missing_in_database": rac.get("rac_hunt_codes_missing_in_database"),
        "rac_numeric_mismatch_rows": rac.get("numeric_mismatch_rows"),
        "rac_significant_difference_rows_abs_delta_gt_5": rac.get("significant_difference_rows_abs_delta_gt_5"),
        "truth_source_family_summary": truth.get("families", {}),
    }
    if rac.get("rac_hunt_codes_missing_in_database") not in (0, None):
        blockers.append("RAC hunt codes missing from DATABASE.csv")
    if rac.get("numeric_mismatch_rows") not in (0, None):
        blockers.append("RAC numeric mismatches remain against DATABASE.csv")
    for family, item in (truth.get("families") or {}).items():
        if item.get("mismatch_rows_after_promotion") not in (0, None):
            blockers.append(f"{family} truth-source mismatches after promotion: {item.get('mismatch_rows_after_promotion')}")
        if item.get("structural_duplicated_by_residency_errors") not in (0, None):
            blockers.append(f"{family} structural duplicated-by-residency errors: {item.get('structural_duplicated_by_residency_errors')}")
        if family == "antlerless_elk_control_units" and item.get("warnings"):
            warnings.append(f"Control-unit overlay unresolved warnings retained: {', '.join(item.get('warnings'))}")

    database_to_runtime = {
        "permit_integrity_database_rows": permits.get("database_rows"),
        "permit_integrity_database_unique_hunt_codes": permits.get("database_unique_hunt_codes"),
        "permit_integrity_promotion_blocker_count": permits.get("promotion_blocker_count"),
        "permit_integrity_mismatches_after_sync": (permits.get("totals") or {}).get("mismatches_after_sync"),
        "antlerless_elk_database_difference_rows": antlerless_elk.get("database_difference_rows"),
        "antlerless_elk_runtime_difference_rows": antlerless_elk.get("runtime_difference_rows"),
        "antlerless_elk_runtime_status_counts": antlerless_elk.get("runtime_status_counts"),
    }
    if permits.get("promotion_blocker_count") not in (0, None):
        blockers.append("Permit allocation integrity blockers remain")
    if (permits.get("totals") or {}).get("mismatches_after_sync") not in (0, None):
        blockers.append("Permit allocation runtime mismatches remain")
    if antlerless_elk.get("database_difference_rows") not in (0, None):
        blockers.append("Antlerless elk database differences remain")
    if antlerless_elk.get("runtime_difference_rows") not in (0, None):
        blockers.append("Antlerless elk runtime differences remain")

    ml_rows = read_csv("processed_data/ml_draw_predictions_v1.csv")
    predictive_rows = read_csv("processed_data/draw_reality_engine_predictive_v2.csv")
    probability = count_probability_violations(ml_rows)
    duplicate_keys = {
        "ml_draw_predictions_v1": duplicate_key_count(ml_rows),
        "draw_reality_engine_predictive_v2": duplicate_key_count(predictive_rows),
    }
    if probability["null_probability_violation_count"]:
        blockers.append("Rows that should have null draw-probability fields still have probabilities")
    if any(duplicate_keys.values()):
        blockers.append("Duplicate prediction keys remain")

    draw_family = draw_family_check()
    if draw_family["old_internal_label_hit_count"]:
        blockers.append("Old internal draw_family labels remain")

    sensitive = sensitive_row_checks()
    if sensitive["failed_count"]:
        blockers.append("Sensitive row checks failed")

    semantic_guardrails = {
        "row_counts": gpt.get("row_counts"),
        "coverage_modeled_availability": coverage.get("modeled_availability"),
        "availability_review_conclusion": availability.get("conclusion"),
        "probability_guardrails": probability,
        "duplicate_key_counts": duplicate_keys,
        "draw_family": draw_family,
        "sensitive_rows": sensitive,
    }

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "publish_ready": len(blockers) == 0,
        "blockers": blockers,
        "warnings": warnings,
        "source_to_database": source_to_database,
        "database_to_runtime": database_to_runtime,
        "semantic_guardrails": semantic_guardrails,
        "validation_commands_expected": command_inventory(),
    }
    return report


def write_md(report: dict[str, Any]) -> str:
    ready = "YES" if report["publish_ready"] else "NO"
    lines = [
        "# Database Publish Readiness Report",
        "",
        f"Generated UTC: {report['generated_at_utc']}",
        f"Publish ready: **{ready}**",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- {item}" for item in report["blockers"]] if report["blockers"] else ["- None"])
    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    lines.extend([f"- {item}" for item in report["warnings"]] if report["warnings"] else ["- None"])
    lines.extend(
        [
            "",
        "## Source To Database",
        "",
        f"- Database rows: {report['source_to_database']['database_rows']}",
        f"- Database unique hunt codes: {report['source_to_database']['database_unique_hunt_codes']}",
        f"- RAC hunt codes missing in database: {report['source_to_database']['rac_hunt_codes_missing_in_database']}",
        f"- RAC numeric mismatch rows: {report['source_to_database']['rac_numeric_mismatch_rows']}",
        f"- RAC significant differences > 5: {report['source_to_database']['rac_significant_difference_rows_abs_delta_gt_5']}",
        "",
        "## Database To Runtime",
        "",
        f"- Permit integrity blockers: {report['database_to_runtime']['permit_integrity_promotion_blocker_count']}",
        f"- Permit integrity mismatches after sync: {report['database_to_runtime']['permit_integrity_mismatches_after_sync']}",
        f"- Antlerless elk database differences: {report['database_to_runtime']['antlerless_elk_database_difference_rows']}",
        f"- Antlerless elk runtime differences: {report['database_to_runtime']['antlerless_elk_runtime_difference_rows']}",
        "",
        "## Guardrails",
        "",
        f"- Null-probability violations: {report['semantic_guardrails']['probability_guardrails']['null_probability_violation_count']}",
        f"- `ml_draw_predictions_v1` duplicate keys: {report['semantic_guardrails']['duplicate_key_counts']['ml_draw_predictions_v1']}",
        f"- `draw_reality_engine_predictive_v2` duplicate keys: {report['semantic_guardrails']['duplicate_key_counts']['draw_reality_engine_predictive_v2']}",
        f"- Old internal draw-family label hits: {report['semantic_guardrails']['draw_family']['old_internal_label_hit_count']}",
        f"- Sensitive row failed checks: {report['semantic_guardrails']['sensitive_rows']['failed_count']}",
        "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build_report()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(write_md(report), encoding="utf-8")
    print(json.dumps({"publish_ready": report["publish_ready"], "blockers": report["blockers"], "warnings": report["warnings"], "json": str(OUT_JSON.relative_to(ROOT)), "md": str(OUT_MD.relative_to(ROOT))}, indent=2))
    return 0 if report["publish_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
