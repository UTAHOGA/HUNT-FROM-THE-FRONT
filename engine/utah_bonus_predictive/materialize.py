"""Formal materialization CLI for Utah bonus predictive outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from engine.utah_draw_predictive.classifier import sanitize_modeled_probability_fields
from engine.utah_draw_predictive.preference_antlerless import build_preference_antlerless_predictions
from engine.utah_draw_predictive.preference_general_deer import build_preference_general_deer_predictions

from .backtest import build_backtest_rows
from .forecast import (
    REPO,
    build_above_index,
    build_truth_indexes,
    materialize_prediction_rows,
    normalize_history_years,
    read_csv,
    run_official_forecast_build,
    write_csv,
)
from .rules import MODEL_VERSION, RULE_VERSION
from .split import split_utah_bonus_permits


TRUTH_PATH = REPO / "data_truth" / "draw_results_truth" / "normalized" / "draw_results_long.csv"
RUNTIME_DRAFT_DIR = REPO / "data_model" / "runtime_drafts"
DATABASE_2026_PATH = REPO / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
TARGET_HUNT_TOKENS = (
    "once-in-a-lifetime",
    "once in a lifetime",
    "oial",
    "limited entry",
    "premium limited entry",
)


def status_from_probability(max_point_permits: int, random_permits: int, p_bonus_pool: float) -> str:
    if max_point_permits == 0 and random_permits > 0:
        return "RANDOM ONLY"
    if p_bonus_pool >= 0.999:
        return "MAX POOL"
    if p_bonus_pool > 0:
        return "ON EDGE"
    return "BEHIND"


def build_report(
    prediction_rows: list[dict[str, object]],
    forecast_year: int,
    history_years: list[int],
    source_path: Path,
    command_used: str,
) -> dict[str, object]:
    return {
        "rows": len(prediction_rows),
        "unique_hunt_codes": len({row["hunt_code"] for row in prediction_rows}),
        "years": sorted({str(row["year"]) for row in prediction_rows}),
        "forecast_year": forecast_year,
        "source_years": f"{min(history_years)}-{max(history_years)}",
        "source_years_used_nonnull": sum(1 for row in prediction_rows if str(row.get("source_years_used", "")).strip() != ""),
        "source": str(source_path.relative_to(REPO)),
        "command_used": command_used,
    }


def _nonnull(rows: list[dict[str, object]], column: str) -> int:
    return sum(1 for row in rows if str(row.get(column, "")).strip() != "")


def _duplicate_count(rows: list[dict[str, object]], fields: list[str]) -> int:
    keys = [tuple(str(row.get(field, "")).strip() for field in fields) for row in rows]
    return len(keys) - len(set(keys))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _quota_info(row: dict[str, str]) -> tuple[bool, bool]:
    raw_res = str(row.get("permits_2026_res", "")).strip()
    raw_nr = str(row.get("permits_2026_nr", "")).strip()
    raw_total = str(row.get("permits_2026_total", "")).strip()
    quota_blank = raw_res == "" and raw_nr == "" and raw_total == ""
    total = 0
    for value in (raw_res, raw_nr, raw_total):
        try:
            if value != "":
                total += int(float(value))
        except Exception:
            continue
    return quota_blank, total > 0


def _is_target_bonus_hunt(hunt_type: str) -> bool:
    value = str(hunt_type or "").strip().lower()
    return any(token in value for token in TARGET_HUNT_TOKENS)


def _build_coverage_report(
    db_rows: list[dict[str, str]],
    backtest_rows: list[dict[str, object]],
    prediction_rows: list[dict[str, object]],
    output_dir: Path,
    forecast_year: int,
) -> dict[str, object]:
    forecast_codes = {str(row["hunt_code"]).strip().upper() for row in prediction_rows if str(row.get("hunt_code", "")).strip()}
    backtest_codes = {str(row["hunt_code"]).strip().upper() for row in backtest_rows if str(row.get("hunt_code", "")).strip()}
    db_by_code: dict[str, dict[str, str]] = {}
    for row in db_rows:
        code = str(row.get("hunt_code", "")).strip().upper()
        if code and code not in db_by_code:
            db_by_code[code] = row

    coverage_rows: list[dict[str, object]] = []
    current_db_codes = set(db_by_code.keys())
    coverage_universe = sorted(forecast_codes | backtest_codes | current_db_codes)
    active_forecast_eligible_codes = 0
    forecast_label = str(forecast_year)
    forecast_eligible_field = f"forecast_eligible_{forecast_label}"
    not_active_reason = f"not_active_in_{forecast_label}"
    total_active_key = f"total_active_{forecast_label}_forecast_eligible_hunt_codes"
    count_not_active_key = f"count_excluded_not_active_in_{forecast_label}"

    reason_counts = {
        "included_forecast": 0,
        "not_OIL_LE_PLE": 0,
        not_active_reason: 0,
        "missing_forecast_quota": 0,
        "missing_required_metadata": 0,
        "hunt_code_changed_or_not_crosswalked": 0,
        "other_missing_model_input": 0,
    }

    for code in coverage_universe:
        db_row = db_by_code.get(code)
        in_forecast = code in forecast_codes
        in_backtest = code in backtest_codes
        in_current_db = db_row is not None
        hunt_type = str(db_row.get("hunt_type", "") if db_row else "")
        hunt_name = str(db_row.get("hunt_name", "") if db_row else "")
        species = str(db_row.get("species", "") if db_row else "")
        metadata_ok = bool(code and hunt_type.strip() and hunt_name.strip() and species.strip())
        is_target = _is_target_bonus_hunt(hunt_type) if db_row else False
        quota_blank, has_positive_quota = _quota_info(db_row) if db_row else (False, False)
        forecast_eligible = in_current_db and metadata_ok and is_target and not quota_blank and has_positive_quota
        if forecast_eligible:
            active_forecast_eligible_codes += 1

        if in_forecast:
            reason = "included_forecast"
        elif not in_current_db:
            reason = "hunt_code_changed_or_not_crosswalked"
        elif not metadata_ok:
            reason = "missing_required_metadata"
        elif not is_target:
            reason = "not_OIL_LE_PLE"
        elif quota_blank:
            reason = "missing_forecast_quota"
        elif not has_positive_quota:
            reason = not_active_reason
        else:
            reason = "other_missing_model_input"

        reason_counts[reason] += 1
        coverage_rows.append(
            {
                "hunt_code": code,
                "in_forecast": in_forecast,
                "in_backtest": in_backtest,
                "in_current_database": in_current_db,
                forecast_eligible_field: forecast_eligible,
                "exclusion_reason": reason,
                "hunt_type": hunt_type,
                "species": species,
                "hunt_name": hunt_name,
                "permits_2026_res": "" if not db_row else db_row.get("permits_2026_res", ""),
                "permits_2026_nr": "" if not db_row else db_row.get("permits_2026_nr", ""),
                "permits_2026_total": "" if not db_row else db_row.get("permits_2026_total", ""),
            }
        )

    coverage_csv_path = output_dir / "predictive_coverage_report.csv"
    write_csv(
        coverage_csv_path,
        coverage_rows,
        [
            "hunt_code",
            "in_forecast",
            "in_backtest",
            "in_current_database",
            forecast_eligible_field,
            "exclusion_reason",
            "hunt_type",
            "species",
            "hunt_name",
            "permits_2026_res",
            "permits_2026_nr",
            "permits_2026_total",
        ],
    )

    coverage_report = {
        "total_historical_backtest_hunt_codes": len(backtest_codes),
        "total_forecast_hunt_codes": len(forecast_codes),
        total_active_key: active_forecast_eligible_codes,
        "count_excluded_not_OIL_LE_PLE": reason_counts["not_OIL_LE_PLE"],
        count_not_active_key: reason_counts[not_active_reason],
        "count_excluded_missing_forecast_quota": reason_counts["missing_forecast_quota"],
        "count_excluded_missing_required_metadata": reason_counts["missing_required_metadata"],
        "count_excluded_hunt_code_changed_or_not_crosswalked": reason_counts["hunt_code_changed_or_not_crosswalked"],
        "count_excluded_other_reason": reason_counts["other_missing_model_input"],
        "count_excluded_missing_model_input_or_not_in_predictive_draft": reason_counts["other_missing_model_input"],
        "forecast_codes_match_active_eligible_universe": len(forecast_codes) == active_forecast_eligible_codes,
        "active_eligible_codes_missing_from_forecast": max(0, active_forecast_eligible_codes - len(forecast_codes)),
        "forecast_codes_outside_active_eligible_universe": max(0, len(forecast_codes) - active_forecast_eligible_codes),
        "reason_counts": reason_counts,
        "source_csv": _safe_relative(coverage_csv_path),
    }
    coverage_json_path = output_dir / "predictive_coverage_report.json"
    coverage_json_path.write_text(json.dumps(coverage_report, indent=2), encoding="utf-8")
    return {
        "json_path": coverage_json_path,
        "csv_path": coverage_csv_path,
        "report": coverage_report,
    }


def _eb3024_regression(truth_rows: list[dict[str, str]]) -> dict[str, object]:
    permits: dict[tuple[str, str], dict[str, int]] = {}
    points: dict[tuple[str, str, str], dict[str, int]] = {}
    for row in truth_rows:
        if str(row.get("hunt_code", "")).strip().upper() != "EB3024":
            continue
        year = str(row.get("year", "")).strip()
        residency = str(row.get("residency", "")).strip()
        points_text = str(row.get("points", "")).strip()
        permit_key = (year, residency)
        point_key = (year, residency, points_text)
        permits.setdefault(permit_key, {"public": 0, "bonus": 0, "regular": 0})
        points.setdefault(point_key, {"eligible": 0, "bonus": 0, "regular": 0})
        permits[permit_key]["public"] += int(float(row.get("total_permits") or 0))
        permits[permit_key]["bonus"] += int(float(row.get("bonus_permits") or 0))
        permits[permit_key]["regular"] += int(float(row.get("regular_permits") or 0))
        if points_text:
            points[point_key]["eligible"] += int(float(row.get("eligible_applicants") or 0))
            points[point_key]["bonus"] += int(float(row.get("bonus_permits") or 0))
            points[point_key]["regular"] += int(float(row.get("regular_permits") or 0))

    unsuccessful_2024_28 = points[("2024", "Resident", "28")]["eligible"] - points[("2024", "Resident", "28")]["bonus"] - points[("2024", "Resident", "28")]["regular"]
    retention = points[("2025", "Resident", "29")]["eligible"] / max(1, unsuccessful_2024_28)
    return {
        "pass": (
            permits[("2024", "Resident")] == {"public": 7, "bonus": 4, "regular": 3}
            and permits[("2025", "Resident")] == {"public": 9, "bonus": 5, "regular": 4}
            and permits[("2024", "Nonresident")] == {"public": 1, "bonus": 0, "regular": 1}
            and permits[("2025", "Nonresident")] == {"public": 1, "bonus": 0, "regular": 1}
            and unsuccessful_2024_28 == 6
            and round(retention, 6) == 0.833333
        ),
        "resident_2024": permits[("2024", "Resident")],
        "resident_2025": permits[("2025", "Resident")],
        "nonresident_2024": permits[("2024", "Nonresident")],
        "nonresident_2025": permits[("2025", "Nonresident")],
        "unsuccessful_2024_28": unsuccessful_2024_28,
        "retention_2024_28_to_2025_29": round(retention, 6),
    }


def _ui_probability_checks() -> dict[str, object]:
    text = (REPO / "hunt-research.js").read_text(encoding="utf-8")
    precedence_ok = all(
        token in text
        for token in [
            "const pDrawPct = num(firstAvailable(row, ['p_draw_pct']))",
            "const pDraw = num(firstAvailable(row, ['p_draw']))",
            "p_bonus_pool_pct",
            "pool_breakdown",
            "odds_2026_projected",
        ]
    )
    max_pool_force_absent = "if (row.status === 'MAX POOL') return 100;" not in text and 'status == "MAX POOL"' not in text
    return {
        "precedence_ok": precedence_ok,
        "max_pool_force_100_absent": max_pool_force_absent,
    }


def _anomaly_counts(prediction_rows: list[dict[str, object]], backtest_rows: list[dict[str, object]]) -> dict[str, object]:
    prediction_anomalies = {
        "p_draw_outside_0_1": 0,
        "p_draw_pct_outside_0_100": 0,
        "p_draw_pct_null": 0,
        "public_permits_gt_0_but_p_draw_null": 0,
        "status_max_pool_and_p_draw_pct_100": 0,
        "status_max_pool_and_p_draw_pct_lt_100": 0,
        "random_permits_gt_0_and_p_random_pool_0": 0,
        "duplicate_key_count": _duplicate_count(prediction_rows, ["hunt_code", "residency", "points"]),
    }
    for row in prediction_rows:
        p_draw = None
        p_draw_pct = None
        p_random_pool = None
        public_permits = 0
        random_permits = 0
        try:
            p_draw = float(str(row.get("p_draw", "")).strip()) if str(row.get("p_draw", "")).strip() != "" else None
        except Exception:
            p_draw = None
        try:
            p_draw_pct = float(str(row.get("p_draw_pct", "")).strip()) if str(row.get("p_draw_pct", "")).strip() != "" else None
        except Exception:
            p_draw_pct = None
        try:
            p_random_pool = float(str(row.get("p_random_pool", "")).strip()) if str(row.get("p_random_pool", "")).strip() != "" else None
        except Exception:
            p_random_pool = None
        try:
            public_permits = int(float(row.get("public_permits_2026") or 0))
            random_permits = int(float(row.get("random_permits_2026") or 0))
        except Exception:
            pass
        if p_draw is not None and not (0.0 <= p_draw <= 1.0):
            prediction_anomalies["p_draw_outside_0_1"] += 1
        if p_draw_pct is None:
            prediction_anomalies["p_draw_pct_null"] += 1
        elif not (0.0 <= p_draw_pct <= 100.0):
            prediction_anomalies["p_draw_pct_outside_0_100"] += 1
        if public_permits > 0 and p_draw is None:
            prediction_anomalies["public_permits_gt_0_but_p_draw_null"] += 1
        if str(row.get("status", "")).strip().upper() == "MAX POOL":
            if p_draw_pct == 100.0:
                prediction_anomalies["status_max_pool_and_p_draw_pct_100"] += 1
            if p_draw_pct is not None and p_draw_pct < 100.0:
                prediction_anomalies["status_max_pool_and_p_draw_pct_lt_100"] += 1
        if random_permits > 0 and p_random_pool == 0.0:
            prediction_anomalies["random_permits_gt_0_and_p_random_pool_0"] += 1

    backtest_anomalies = {
        "calibration_error_by_probability_bucket_null": sum(
            1 for row in backtest_rows if str(row.get("calibration_error_by_probability_bucket", "")).strip() == ""
        ),
        "brier_score_by_point_level_null": sum(1 for row in backtest_rows if str(row.get("brier_score_by_point_level", "")).strip() == ""),
        "guaranteed_at_error_null": sum(1 for row in backtest_rows if str(row.get("guaranteed_at_error", "")).strip() == ""),
        "year_transitions_tested": sorted({str(row.get("year_transition", "")).strip() for row in backtest_rows if str(row.get("year_transition", "")).strip()}),
        "distinct_hunt_code_count": len({str(row.get("hunt_code", "")).strip() for row in backtest_rows if str(row.get("hunt_code", "")).strip()}),
        "distinct_residency_count": len({str(row.get("residency", "")).strip() for row in backtest_rows if str(row.get("residency", "")).strip()}),
    }
    return {
        "prediction": prediction_anomalies,
        "backtest": backtest_anomalies,
    }


def _build_manifest(
    output_dir: Path,
    command_used: str,
    forecast_year: int,
    history_years: list[int],
    prediction_rows: list[dict[str, object]],
    backtest_rows: list[dict[str, object]],
    successor_rows: list[dict[str, object]],
    coverage_report: dict[str, object],
    eb3024: dict[str, object],
    ui_checks: dict[str, object],
    runtime_truth_copy: Path,
    prediction_input: Path,
) -> Path:
    output_files = {
        "ml_draw_predictions_v1.csv": output_dir / "ml_draw_predictions_v1.csv",
        "ml_draw_predictions_v1_report.json": output_dir / "ml_draw_predictions_v1_report.json",
        "backtest_utah_bonus_draw.csv": output_dir / "backtest_utah_bonus_draw.csv",
        "backtest_utah_bonus_draw_report.json": output_dir / "backtest_utah_bonus_draw_report.json",
        "draw_reality_engine_predictive_v2.csv": output_dir / "draw_reality_engine_predictive_v2.csv",
        "draw_reality_engine_v2.csv": runtime_truth_copy,
        "predictive_coverage_report.json": output_dir / "predictive_coverage_report.json",
        "predictive_coverage_report.csv": output_dir / "predictive_coverage_report.csv",
    }
    anomalies = _anomaly_counts(prediction_rows, backtest_rows)
    manifest = {
        "model_version": MODEL_VERSION,
        "rule_version": RULE_VERSION,
        "forecast_year": forecast_year,
        "source_years": history_years,
        "command_used": command_used,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_files": {name: _safe_relative(path) for name, path in output_files.items()},
        "output_row_counts": {
            "ml_draw_predictions_v1.csv": len(prediction_rows),
            "backtest_utah_bonus_draw.csv": len(backtest_rows),
            "draw_reality_engine_predictive_v2.csv": len(successor_rows),
            "draw_reality_engine_v2.csv": len(read_csv(runtime_truth_copy)),
        },
        "duplicate_key_counts": {
            "ml_draw_predictions_v1.csv": _duplicate_count(prediction_rows, ["hunt_code", "residency", "points"]),
            "draw_reality_engine_predictive_v2.csv": _duplicate_count(successor_rows, ["hunt_code", "residency", "points"]),
        },
        "p_draw_non_null_count": _nonnull(prediction_rows, "p_draw"),
        "p_draw_pct_non_null_count": _nonnull(prediction_rows, "p_draw_pct"),
        "calibration_metric_non_null_count": _nonnull(backtest_rows, "calibration_error_by_probability_bucket"),
        "EB3024_regression_result": eb3024,
        "one_permit_random_only_result": {
            "pass": split_utah_bonus_permits(1).maxPointPermits == 0 and split_utah_bonus_permits(1).randomPermits == 1,
        },
        "MAX_POOL_safety_result": {
            "pass": ui_checks["max_pool_force_100_absent"],
        },
        "UI_precedence_result": ui_checks,
        "coverage_report_summary": coverage_report,
        "anomaly_checks": anomalies,
        "source_files_used": {
            _safe_relative(TRUTH_PATH): _sha256_file(TRUTH_PATH),
            _safe_relative(DATABASE_2026_PATH): _sha256_file(DATABASE_2026_PATH),
            _safe_relative(runtime_truth_copy): _sha256_file(runtime_truth_copy),
            _safe_relative(prediction_input): _sha256_file(prediction_input),
            "hunt-research.js": _sha256_file(REPO / "hunt-research.js"),
            "config.js": _sha256_file(REPO / "config.js"),
        },
    }
    manifest_path = output_dir / "utah_bonus_predictive_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def materialize_outputs(
    output_dir: Path,
    forecast_year: int,
    history_years: list[int],
    command_used: str,
    run_upstream: bool = True,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_paths = run_official_forecast_build(forecast_year, RUNTIME_DRAFT_DIR) if run_upstream else {
        "prediction_rows": RUNTIME_DRAFT_DIR / f"predictive_bonus_engine_{forecast_year}.predictions.csv",
        "materialized_rows": RUNTIME_DRAFT_DIR / f"predictive_bonus_engine_{forecast_year}.materialized.csv",
        "audit_rows": RUNTIME_DRAFT_DIR / f"predictive_bonus_engine_{forecast_year}.audit.csv",
    }

    truth_rows = read_csv(TRUTH_PATH)
    permits, ladders, meta = build_truth_indexes(truth_rows)
    above_index = build_above_index(ladders)

    ml_input_rows = read_csv(runtime_paths["materialized_rows"])
    source_years_used = ",".join(str(year) for year in history_years)
    prediction_rows, successor_rows = materialize_prediction_rows(
        ml_rows=ml_input_rows,
        permits=permits,
        ladders=ladders,
        above_index=above_index,
        meta=meta,
        forecast_year=forecast_year,
        source_years_used=source_years_used,
        earliest_source_year=min(history_years),
        latest_source_year=max(history_years),
    )

    db_rows = read_csv(DATABASE_2026_PATH)
    preference_general_deer_rows = build_preference_general_deer_predictions(
        truth_rows=truth_rows,
        db_rows=db_rows,
        forecast_year=forecast_year,
        history_years=history_years,
    )
    preference_antlerless_rows = build_preference_antlerless_predictions(
        truth_rows=truth_rows,
        db_rows=db_rows,
        forecast_year=forecast_year,
        history_years=history_years,
    )
    if preference_general_deer_rows:
        preference_general_deer_rows = [sanitize_modeled_probability_fields(dict(row)) for row in preference_general_deer_rows]
        prediction_rows.extend(preference_general_deer_rows)
        successor_rows.extend(dict(row) for row in preference_general_deer_rows)
    if preference_antlerless_rows:
        preference_antlerless_rows = [sanitize_modeled_probability_fields(dict(row)) for row in preference_antlerless_rows]
        prediction_rows.extend(preference_antlerless_rows)
        successor_rows.extend(dict(row) for row in preference_antlerless_rows)
    if preference_general_deer_rows or preference_antlerless_rows:
        prediction_rows.sort(key=lambda row: (str(row.get("hunt_code", "")), str(row.get("residency", "")), int(float(str(row.get("points", 0)) or 0))))
        successor_rows.sort(key=lambda row: (str(row.get("hunt_code", "")), str(row.get("residency", "")), int(float(str(row.get("points", 0)) or 0))))

    prediction_fields = [
        "model_version",
        "rule_version",
        "year",
        "forecast_year",
        "hunt_code",
        "hunt_name",
        "species",
        "sex_type",
        "hunt_type",
        "hunt_class",
        "residency",
        "points",
        "draw_pool",
        "public_permits_2025",
        "public_permits_2026",
        "max_point_permits_2025",
        "max_point_permits_2026",
        "random_permits_2025",
        "random_permits_2026",
        "guaranteed_at_2025",
        "guaranteed_at_2026",
        "applicants_above",
        "applicants_at_level",
        "p_bonus_pool",
        "p_random_pool",
        "p_draw",
        "p_bonus_pool_pct",
        "p_random_pool_pct",
        "p_draw_pct",
        "random_draw_odds_2026",
        "gap",
        "delta_gap",
        "status",
        "trend",
        "draw_outlook",
        "source_years_used",
        "source_year_count",
        "latest_source_year",
        "earliest_source_year",
        "source_dataset",
        "model_strategy",
        "preference_model_valid",
        "preference_model_note",
        "weapon",
        "draw_system_type",
        "algorithm_status",
        "target_scope",
        "modeled_by_engine",
        "reason",
    ]
    ml_predictions_path = output_dir / "ml_draw_predictions_v1.csv"
    write_csv(ml_predictions_path, prediction_rows, prediction_fields)

    report = build_report(prediction_rows, forecast_year, history_years, runtime_paths["materialized_rows"], command_used)
    ml_report_path = output_dir / "ml_draw_predictions_v1_report.json"
    ml_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    successor_path = output_dir / "draw_reality_engine_predictive_v2.csv"
    successor_fields = list(dict.fromkeys(key for row in successor_rows for key in row.keys())) if successor_rows else []
    write_csv(successor_path, successor_rows, successor_fields)

    backtest_rows = build_backtest_rows(permits, ladders, lambda public_permits: (split_utah_bonus_permits(public_permits).maxPointPermits, split_utah_bonus_permits(public_permits).randomPermits))
    backtest_fields = [
        "from_year",
        "to_year",
        "year_transition",
        "hunt_code",
        "residency",
        "mean_absolute_error_applicants_at_level",
        "mean_absolute_error_applicants_above",
        "bonus_pool_cutoff_error",
        "guaranteed_at_error",
        "quota_split_error",
        "brier_score_by_point_level",
        "calibration_error_by_probability_bucket",
    ]
    backtest_csv_path = output_dir / "backtest_utah_bonus_draw.csv"
    write_csv(backtest_csv_path, backtest_rows, backtest_fields)

    backtest_report = {
        "rows": len(backtest_rows),
        "year_transitions_tested": sorted({row["year_transition"] for row in backtest_rows}),
        "distinct_hunt_code": len({row["hunt_code"] for row in backtest_rows}),
        "distinct_residency": len({row["residency"] for row in backtest_rows}),
        "nonnull_counts": {
            "mean_absolute_error_applicants_at_level": sum(1 for row in backtest_rows if str(row["mean_absolute_error_applicants_at_level"]).strip() != ""),
            "mean_absolute_error_applicants_above": sum(1 for row in backtest_rows if str(row["mean_absolute_error_applicants_above"]).strip() != ""),
            "bonus_pool_cutoff_error": sum(1 for row in backtest_rows if str(row["bonus_pool_cutoff_error"]).strip() != ""),
            "guaranteed_at_error": sum(1 for row in backtest_rows if str(row["guaranteed_at_error"]).strip() != ""),
            "quota_split_error": sum(1 for row in backtest_rows if str(row["quota_split_error"]).strip() != ""),
            "brier_score_by_point_level": sum(1 for row in backtest_rows if str(row["brier_score_by_point_level"]).strip() != ""),
            "calibration_error_by_probability_bucket": sum(
                1 for row in backtest_rows if str(row["calibration_error_by_probability_bucket"]).strip() != ""
            ),
        },
    }
    backtest_report_path = output_dir / "backtest_utah_bonus_draw_report.json"
    backtest_report_path.write_text(json.dumps(backtest_report, indent=2), encoding="utf-8")

    runtime_truth_source = RUNTIME_DRAFT_DIR / "draw_reality_engine_v2.csv"
    runtime_truth_copy = output_dir / "draw_reality_engine_v2.csv"
    shutil.copy2(runtime_truth_source, runtime_truth_copy)

    coverage_artifacts = _build_coverage_report(db_rows, backtest_rows, prediction_rows, output_dir, forecast_year)
    eb3024 = _eb3024_regression(truth_rows)
    ui_checks = _ui_probability_checks()
    manifest_path = _build_manifest(
        output_dir=output_dir,
        command_used=command_used,
        forecast_year=forecast_year,
        history_years=history_years,
        prediction_rows=prediction_rows,
        backtest_rows=backtest_rows,
        successor_rows=successor_rows,
        coverage_report=coverage_artifacts["report"],
        eb3024=eb3024,
        ui_checks=ui_checks,
        runtime_truth_copy=runtime_truth_copy,
        prediction_input=runtime_paths["materialized_rows"],
    )

    return {
        "ml_predictions": ml_predictions_path,
        "ml_report": ml_report_path,
        "backtest_csv": backtest_csv_path,
        "backtest_report": backtest_report_path,
        "predictive_successor": successor_path,
        "runtime_truth_v2": runtime_truth_copy,
        "prediction_input": runtime_paths["materialized_rows"],
        "coverage_report_json": coverage_artifacts["json_path"],
        "coverage_report_csv": coverage_artifacts["csv_path"],
        "manifest": manifest_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO / "processed_data"))
    parser.add_argument("--forecast-year", type=int, default=2026)
    parser.add_argument("--history-years", default="2021,2022,2023,2024,2025")
    parser.add_argument("--skip-upstream", action="store_true")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--rule-version", default=RULE_VERSION)
    args = parser.parse_args()

    history_years = normalize_history_years(args.history_years)
    command_used = "python -m engine.utah_bonus_predictive.materialize " + " ".join(
        [
            f"--output-dir {args.output_dir}",
            f"--forecast-year {args.forecast_year}",
            f"--history-years {args.history_years}",
            "--skip-upstream" if args.skip_upstream else "",
        ]
    ).strip()
    artifacts = materialize_outputs(
        output_dir=Path(args.output_dir),
        forecast_year=args.forecast_year,
        history_years=history_years,
        command_used=command_used,
        run_upstream=not args.skip_upstream,
    )
    print(json.dumps({key: str(value) for key, value in artifacts.items()}, indent=2))


if __name__ == "__main__":
    main()
