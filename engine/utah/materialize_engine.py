"""Materialize Utah predictive hunt research engine V1 outputs."""

from __future__ import annotations

import argparse
import csv
import io
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Mapping, Optional

from .decision_score import score_application_value
from .forecast_demand import forecast_demand
from .forecast_permits import forecast_permits
from .quality_score import compute_hunt_quality_score, compute_permit_stability_score
from .rules import classify_utah_draw_rule
from .schema import BonusDrawInput, normalize_hunt_code, to_float, to_int
from .simulate_bonus_draw import compute_bonus_draw_probability, odds_percent
from .validation import validate_hunt_code_preservation, validate_required_output_files


DRAW_OUTPUT = "draw_prediction_engine_v1.csv"
DECISION_OUTPUT = "hunt_decision_scores_v1.csv"
POINT_CREEP_OUTPUT = "point_creep_forecast_v1.csv"
REPORT_OUTPUT = "model_run_report_v1.json"


def _safe_read_csv(path: Path, warnings: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        warnings.append(f"missing_optional_file:{path.name}")
        return []
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    filtered = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("<<<<<<<") or stripped.startswith("=======") or stripped.startswith(">>>>>>>"):
            warnings.append(f"filtered_merge_marker:{path.name}")
            continue
        filtered.append(line)
    if not filtered:
        warnings.append(f"empty_file:{path.name}")
        return []
    reader = csv.DictReader(io.StringIO("\n".join(filtered)))
    if not reader.fieldnames:
        warnings.append(f"invalid_csv_header:{path.name}")
        return []
    return [dict(row) for row in reader]


def _safe_read_json(path: Path, warnings: list[str]) -> object:
    if not path.exists():
        warnings.append(f"missing_optional_file:{path.name}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        warnings.append(f"invalid_json:{path.name}")
        return {}


def _row_key(row: Mapping[str, object]) -> tuple[str, str, Optional[int]]:
    return (
        normalize_hunt_code(row.get("hunt_code") or row.get("huntCode")),
        str(row.get("residency") or "Resident").strip() or "Resident",
        to_int(row.get("points") or row.get("apply_with_points")),
    )


def _int0(value: object, default: int = 0) -> int:
    parsed = to_int(value)
    return parsed if parsed is not None else default


def _get_allowed_hunt_codes(
    hunt_master_rows: Iterable[Mapping[str, object]],
    draw_rows: Iterable[Mapping[str, object]],
    canonical_payload: object,
) -> set[str]:
    out: set[str] = set()
    for row in hunt_master_rows:
        code = normalize_hunt_code(row.get("hunt_code"))
        if code:
            out.add(code)
    for row in draw_rows:
        code = normalize_hunt_code(row.get("hunt_code") or row.get("huntCode"))
        if code:
            out.add(code)

    if isinstance(canonical_payload, list):
        for row in canonical_payload:
            if isinstance(row, dict):
                code = normalize_hunt_code(row.get("hunt_code") or row.get("huntCode"))
                if code:
                    out.add(code)
    elif isinstance(canonical_payload, dict):
        for value in canonical_payload.values():
            if isinstance(value, dict):
                code = normalize_hunt_code(value.get("hunt_code") or value.get("huntCode"))
                if code:
                    out.add(code)
    return out


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def materialize_engine(input_dir: Path, output_dir: Path) -> dict[str, object]:
    warnings: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    draw_reality_rows = _safe_read_csv(input_dir / "draw_reality_engine.csv", warnings)
    draw_reality_view_rows = _safe_read_csv(input_dir / "draw_reality_view.csv", warnings)
    point_ladder_rows = _safe_read_csv(input_dir / "point_ladder_view.csv", warnings)
    trend_rows = _safe_read_csv(input_dir / "historical_trend_2025.csv", warnings)
    projected_bonus_rows = _safe_read_csv(input_dir / "projected_bonus_draw_2026_simulated.csv", warnings)
    recommended_permit_rows = _safe_read_csv(input_dir / "recommended_permits_2026.csv", warnings)
    hunt_master_rows = _safe_read_csv(input_dir / "hunt_master_enriched.csv", warnings)

    harvest_rows_2024 = _safe_read_csv(input_dir / "harvest-metrics-2024-bg-report.csv", warnings)
    harvest_rows_2025 = _safe_read_csv(input_dir / "harvest-metrics-2025-prelim.csv", warnings)
    harvest_rows = [*harvest_rows_2025, *harvest_rows_2024]

    canonical_path = input_dir / "hunt-master-canonical.json"
    if not canonical_path.exists():
        canonical_path = input_dir / "hunt-master-canonical-2026-source-of-truth.json"
    canonical_payload = _safe_read_json(canonical_path, warnings)

    all_rows = [*draw_reality_rows, *draw_reality_view_rows, *point_ladder_rows, *trend_rows, *projected_bonus_rows]
    allowed_hunt_codes = _get_allowed_hunt_codes(hunt_master_rows, all_rows, canonical_payload)

    demand_forecasts = forecast_demand([*trend_rows, *draw_reality_rows, *projected_bonus_rows])
    permit_forecasts = forecast_permits(recommended_permit_rows, [*draw_reality_rows, *draw_reality_view_rows, *point_ladder_rows, *hunt_master_rows])

    harvest_by_code: dict[str, dict[str, str]] = {}
    for row in harvest_rows:
        code = normalize_hunt_code(row.get("hunt_code") or row.get("huntCode"))
        if code and code not in harvest_by_code:
            harvest_by_code[code] = dict(row)

    key_to_rows: dict[tuple[str, str, Optional[int]], list[dict[str, str]]] = {}
    for row in all_rows:
        key = _row_key(row)
        if not key[0] or key[2] is None:
            continue
        key_to_rows.setdefault(key, []).append(dict(row))

    draw_output_rows: list[dict[str, object]] = []
    decision_output_rows: list[dict[str, object]] = []
    point_creep_rows: list[dict[str, object]] = []

    for key, rows_for_key in key_to_rows.items():
        hunt_code, residency, points = key
        if allowed_hunt_codes and hunt_code not in allowed_hunt_codes:
            continue

        merged: dict[str, object] = {}
        for row in rows_for_key:
            merged.update(row)

        demand_key = (hunt_code, residency, points)
        demand = demand_forecasts.get(demand_key)
        forecast_applicants = demand.forecast_applicants if demand else None

        permit_fc = permit_forecasts.get(hunt_code)
        forecast_total_permits = permit_fc.forecast_total_permits if permit_fc else None

        eligible_applicants = forecast_applicants
        if eligible_applicants is None:
            eligible_applicants = to_int(
                merged.get("eligible_applicants")
                or merged.get("projected_total_applicants_at_point")
                or merged.get("applicants_at_level")
            )

        bonus_input = BonusDrawInput(
            hunt_code=hunt_code,
            year=to_int(merged.get("projection_year") or merged.get("year") or 2026),
            residency=residency,
            points=points,
            eligible_applicants=eligible_applicants,
            bonus_permits=to_int(merged.get("bonus_permits") or merged.get("projected_bonus_pool_permits") or merged.get("max_point_permits_2026")),
            regular_permits=to_int(merged.get("regular_permits") or merged.get("projected_random_pool_permits") or merged.get("random_permits_2026")),
            total_permits=forecast_total_permits if forecast_total_permits is not None else to_int(merged.get("total_permits") or merged.get("public_permits_2026")),
            total_drawn=to_int(merged.get("total_drawn") or merged.get("projected_guaranteed_draws_at_point")),
            status=str(merged.get("status") or ""),
        )
        sim = compute_bonus_draw_probability(bonus_input)

        trend = str(merged.get("trend") or "").strip().upper() or "YELLOW"
        current_permits = bonus_input.total_permits if bonus_input.total_permits is not None else forecast_total_permits
        prior_permits = to_int(merged.get("public_permits_2025") or merged.get("prior_year_permits"))
        permit_stability = compute_permit_stability_score(current_permits, prior_permits)

        quality = compute_hunt_quality_score(
            harvest_row=harvest_by_code.get(hunt_code),
            trend=trend,
            permit_stability_score=permit_stability,
            species=str(merged.get("species") or ""),
            hunt_class=str(merged.get("hunt_class") or merged.get("hunt_type") or ""),
            draw_system_type=str(merged.get("draw_system_type") or merged.get("draw_2026_system_type") or ""),
        )

        guaranteed_at = to_int(merged.get("guaranteed_at_2026") or merged.get("guaranteed_at_2025"))
        if guaranteed_at is None or points is None:
            point_value_score = 50.0
            point_creep_1yr = 0.0
        else:
            gap = guaranteed_at - points
            point_creep_1yr = float(to_float(merged.get("delta_gap")) or gap)
            point_value_score = max(0.0, min(100.0, 100.0 - (abs(gap) * 8.0)))

        permits_for_opp = current_permits if current_permits is not None else 0
        apps_for_opp = eligible_applicants if eligible_applicants is not None else 0
        demand_opp_score = 0.0 if apps_for_opp <= 0 else max(0.0, min(100.0, (permits_for_opp / apps_for_opp) * 100.0))

        decision = score_application_value(
            p_draw=sim.p_draw,
            hunt_quality_score=quality.hunt_quality_score,
            point_value_score=point_value_score,
            demand_opportunity_score=demand_opp_score,
            permit_stability_score=permit_stability,
            point_creep_1yr=point_creep_1yr,
        )

        rule_system = classify_utah_draw_rule(merged)
        draw_out = {
            "hunt_code": hunt_code,
            "year": sim.year or 2026,
            "residency": residency,
            "points": points,
            "draw_system": rule_system,
            "eligible_applicants": sim.eligible_applicants,
            "bonus_permits": bonus_input.bonus_permits,
            "regular_permits": bonus_input.regular_permits,
            "total_permits": bonus_input.total_permits,
            "total_drawn": sim.total_drawn,
            "observed_probability": sim.observed_probability,
            "smoothed_probability": sim.smoothed_probability,
            "p_draw": sim.p_draw,
            "p_draw_percent": odds_percent(sim.p_draw),
            "max_pool_flag": sim.max_pool_flag,
            "permit_source": permit_fc.source if permit_fc else "none",
            "warning": "" if sim.p_draw is not None else "INSUFFICIENT_DATA",
        }
        draw_output_rows.append(draw_out)

        decision_output_rows.append(
            {
                "hunt_code": hunt_code,
                "year": sim.year or 2026,
                "residency": residency,
                "points": points,
                "application_value_score": decision.application_value_score,
                "decision_label": decision.decision_label,
                "modeled_draw_probability_score": decision.modeled_draw_probability_score,
                "hunt_quality_score": decision.hunt_quality_score,
                "point_value_score": decision.point_value_score,
                "demand_opportunity_score": decision.demand_opportunity_score,
                "permit_stability_score": decision.permit_stability_score,
                "success_rate_score": quality.success_rate_score,
                "harvest_score": quality.harvest_score,
                "hunters_afield_score": quality.hunters_afield_score,
                "days_score": quality.days_score,
                "trend_score": quality.trend_score,
                "age_quality_score": quality.age_quality_score,
                "average_age_harvested": quality.average_age_harvested,
                "age_data_available": quality.age_data_available,
                "age_quality_source_field": quality.age_quality_source_field,
            }
        )

        point_creep_rows.append(
            {
                "hunt_code": hunt_code,
                "year": sim.year or 2026,
                "residency": residency,
                "points": points,
                "point_creep_1yr": round(point_creep_1yr, 3),
                "point_creep_3yr": round(point_creep_1yr * 3.0, 3),
                "forecast_applicants": forecast_applicants,
            }
        )

    draw_validation = validate_hunt_code_preservation(draw_output_rows, allowed_hunt_codes)
    decision_validation = validate_hunt_code_preservation(decision_output_rows, allowed_hunt_codes)
    point_validation = validate_hunt_code_preservation(point_creep_rows, allowed_hunt_codes)

    _write_csv(
        output_dir / DRAW_OUTPUT,
        draw_output_rows,
        [
            "hunt_code",
            "year",
            "residency",
            "points",
            "draw_system",
            "eligible_applicants",
            "bonus_permits",
            "regular_permits",
            "total_permits",
            "total_drawn",
            "observed_probability",
            "smoothed_probability",
            "p_draw",
            "p_draw_percent",
            "max_pool_flag",
            "permit_source",
            "warning",
        ],
    )
    _write_csv(
        output_dir / DECISION_OUTPUT,
        decision_output_rows,
        [
            "hunt_code",
            "year",
            "residency",
            "points",
            "application_value_score",
            "decision_label",
            "modeled_draw_probability_score",
            "hunt_quality_score",
            "point_value_score",
            "demand_opportunity_score",
            "permit_stability_score",
            "success_rate_score",
            "harvest_score",
            "hunters_afield_score",
            "days_score",
            "trend_score",
            "age_quality_score",
            "average_age_harvested",
            "age_data_available",
            "age_quality_source_field",
        ],
    )
    _write_csv(
        output_dir / POINT_CREEP_OUTPUT,
        point_creep_rows,
        [
            "hunt_code",
            "year",
            "residency",
            "points",
            "point_creep_1yr",
            "point_creep_3yr",
            "forecast_applicants",
        ],
    )

    report = {
        "engine_version": "utah_predictive_v1_conservative",
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "warnings": warnings,
        "counts": {
            "allowed_hunt_codes": len(allowed_hunt_codes),
            "draw_prediction_rows": len(draw_output_rows),
            "decision_rows": len(decision_output_rows),
            "point_creep_rows": len(point_creep_rows),
        },
        "validations": {
            "draw_codes_ok": draw_validation.ok,
            "decision_codes_ok": decision_validation.ok,
            "point_creep_codes_ok": point_validation.ok,
            "draw_code_issues": draw_validation.issues[:50],
            "decision_code_issues": decision_validation.issues[:50],
            "point_creep_code_issues": point_validation.issues[:50],
        },
    }
    (output_dir / REPORT_OUTPUT).write_text(json.dumps(report, indent=2), encoding="utf-8")

    outputs_validation = validate_required_output_files(output_dir)
    if not outputs_validation.ok:
        report["warnings"].extend(outputs_validation.issues)
        (output_dir / REPORT_OUTPUT).write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Materialize Utah predictive hunt research engine V1 outputs.")
    parser.add_argument("--input", required=True, help="Input directory (typically processed_data).")
    parser.add_argument("--output", required=True, help="Output directory (typically processed_data/model_outputs).")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    report = materialize_engine(Path(args.input), Path(args.output))
    print(json.dumps({"ok": True, "counts": report.get("counts", {}), "warnings": len(report.get("warnings", []))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
