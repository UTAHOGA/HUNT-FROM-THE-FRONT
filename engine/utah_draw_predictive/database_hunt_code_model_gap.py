"""Canonical database versus modeled hunt-code reconciliation audit."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[2]

MODELED_STATUSES = {
    "MODELED_BONUS",
    "MODELED_PREFERENCE",
    "MODELED_ALLOCATION",
    "MODELED_AVAILABILITY",
    "MODELED_RANDOM_ONLY",
    "MODELED_SPORTSMAN_DRAW",
}
DRAW_ODDS_MODELED_STATUSES = {
    "MODELED_BONUS",
    "MODELED_PREFERENCE",
    "MODELED_SPORTSMAN_DRAW",
    "MODELED_RANDOM_ONLY",
}
PENDING_OR_NON_PROBABILITY_STATUSES = {
    "IN_SCOPE_MODEL_PENDING",
    "MODELED_ALLOCATION",
    "MODELED_AVAILABILITY",
    "EXCLUDED_NOT_PREDICTIVE_DRAW",
    "OUT_OF_SCOPE_NON_TARGET",
}

CANONICAL_DATABASE_CANDIDATES = (
    "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
    "data/hunt-master-canonical-2026-database-candidate.csv",
    "data/hunt-master-canonical-2026-source-of-truth.csv",
    "data/hunt-master-canonical-2026-foundation.csv",
    "processed_data/hunt_master_canonical_2026_SOURCE_OF_TRUTH_FINAL_COMPLETE_NO_PARTIALS.csv",
    "hunt_master_canonical_2026_built.csv",
)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _code(value: object) -> str:
    return _clean(value).upper()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _safe_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def _first_nonblank(row: dict[str, str], fields: Iterable[str]) -> str:
    for field in fields:
        value = _clean(row.get(field))
        if value:
            return value
    return ""


def _choose_canonical_database_file(expected_count: int) -> tuple[Path, list[dict[str, str]], dict[str, int], str]:
    candidate_counts: dict[str, int] = {}
    candidate_rows: dict[str, list[dict[str, str]]] = {}
    for rel_path in CANONICAL_DATABASE_CANDIDATES:
        path = REPO / rel_path
        if not path.exists():
            continue
        rows = _read_csv(path)
        codes = {_code(row.get("hunt_code")) for row in rows if _clean(row.get("hunt_code"))}
        candidate_counts[rel_path] = len(codes)
        candidate_rows[rel_path] = rows

    if not candidate_counts:
        raise FileNotFoundError("No canonical database candidates were found.")

    matching = [rel for rel, count in candidate_counts.items() if count == expected_count]
    if matching:
        selected_rel = matching[0]
        reason = f"Selected canonical database file with expected unique hunt-code count {expected_count}."
    else:
        selected_rel = CANONICAL_DATABASE_CANDIDATES[0]
        if selected_rel not in candidate_counts:
            selected_rel = sorted(candidate_counts.keys())[0]
        reason = (
            f"No canonical database candidate produced the expected hunt-code count {expected_count}; "
            f"selected {selected_rel} as the explicit canonical database source."
        )

    return REPO / selected_rel, candidate_rows[selected_rel], candidate_counts, reason


def _by_hunt_code(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        code = _code(row.get("hunt_code"))
        if code:
            grouped[code].append(row)
    return grouped


def _pick_reason_for_unmodeled(
    hunt_code: str,
    ml_rows: list[dict[str, str]],
    coverage_by_code: dict[str, list[dict[str, str]]],
    present_in_hunt_master: bool,
    present_in_hunt_reference: bool,
) -> tuple[str, str]:
    statuses = {_clean(row.get("algorithm_status")) for row in ml_rows if _clean(row.get("algorithm_status"))}
    draw_system_types = {_clean(row.get("draw_system_type")) for row in ml_rows if _clean(row.get("draw_system_type"))}

    if "IN_SCOPE_MODEL_PENDING" in statuses:
        return "IN_SCOPE_MODEL_PENDING", "Needs strategy implementation before predictive draw-odds modeling."
    if "MODELED_ALLOCATION" in statuses:
        return "MODELED_ALLOCATION_NOT_DRAW_ODDS", "Correctly modeled as allocation-only; keep out of draw-odds modeled totals."
    if "MODELED_AVAILABILITY" in statuses:
        return "MODELED_AVAILABILITY_NOT_DRAW_ODDS", "Correctly modeled as availability/status-only; do not treat as draw-odds modeled."
    if "EXCLUDED_NOT_PREDICTIVE_DRAW" in statuses:
        return "EXCLUDED_NOT_PREDICTIVE_DRAW", "Correctly excluded from predictive draw-odds modeling."
    if "OUT_OF_SCOPE_NON_TARGET" in statuses:
        return "OUT_OF_SCOPE_NON_TARGET", "Correctly out of target prediction scope."

    coverage_rows = coverage_by_code.get(hunt_code, [])
    coverage_predictive = any(_clean(row.get("source_dataset")) == "predictive" for row in coverage_rows)
    coverage_observed = any(_clean(row.get("source_dataset")) == "observed_runtime" for row in coverage_rows)
    coverage_statuses = {_clean(row.get("algorithm_status")) for row in coverage_rows if _clean(row.get("algorithm_status"))}
    coverage_draw_types = {_clean(row.get("draw_system_type")) for row in coverage_rows if _clean(row.get("draw_system_type"))}

    if not coverage_predictive and coverage_observed:
        return "OBSERVED_HISTORY_ONLY", "Appears only in observed-history coverage and is not active in predictive runtime."
    if "UNKNOWN_TARGET_NEEDS_REVIEW" in coverage_statuses or "UNKNOWN_TARGET" in coverage_draw_types:
        return "NEEDS_CLASSIFIER_MAPPING", "Classifier mapping is missing or unresolved for this hunt code."
    if coverage_predictive and not statuses and coverage_draw_types:
        return "NEEDS_STRATEGY_IMPLEMENTATION", "Classified in predictive runtime but strategy does not yet publish modeled rows."
    if draw_system_types and not statuses:
        return "NEEDS_STRATEGY_IMPLEMENTATION", "Draw-system classification exists but strategy implementation is incomplete."
    if not present_in_hunt_master and not present_in_hunt_reference:
        return "DATABASE_ONLY_NOT_IN_ACTIVE_FEED", "Present in canonical database only; absent from active runtime reference surfaces."
    if not present_in_hunt_master or not present_in_hunt_reference:
        return "MISSING_FROM_ACTIVE_2026_SOURCE", "Missing from at least one active 2026 runtime reference surface."
    return "SOURCE_SUPPORT_INSUFFICIENT", "Current source support is insufficient to publish modeled draw-odds rows."


def _bucket_rows(
    bucket: str,
    codes: Iterable[str],
    database_rows_by_code: dict[str, list[dict[str, str]]],
    ml_rows_by_code: dict[str, list[dict[str, str]]],
    dre_rows_by_code: dict[str, list[dict[str, str]]],
    hunt_master_codes: set[str],
    hunt_reference_codes: set[str],
    coverage_by_code: dict[str, list[dict[str, str]]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for hunt_code in sorted(set(codes)):
        db_row = database_rows_by_code.get(hunt_code, [{}])[0]
        ml_rows = ml_rows_by_code.get(hunt_code, [])
        dre_rows = dre_rows_by_code.get(hunt_code, [])
        coverage_rows = coverage_by_code.get(hunt_code, [])

        hunt_name = _first_nonblank(
            db_row if db_row else {},
            ("hunt_name", "title", "unitName"),
        ) or _first_nonblank((ml_rows[0] if ml_rows else {}), ("hunt_name",))
        species = _first_nonblank(db_row if db_row else {}, ("species",)) or _first_nonblank((ml_rows[0] if ml_rows else {}), ("species",))
        permit_type = _first_nonblank(db_row if db_row else {}, ("hunt_type", "permit_type")) or _first_nonblank((ml_rows[0] if ml_rows else {}), ("hunt_type",))

        draw_types = sorted({
            _clean(row.get("draw_system_type"))
            for row in (ml_rows + coverage_rows)
            if _clean(row.get("draw_system_type"))
        })
        statuses = sorted({
            _clean(row.get("algorithm_status"))
            for row in (ml_rows + coverage_rows)
            if _clean(row.get("algorithm_status"))
        })

        present_in_ml = len(ml_rows) > 0
        present_in_dre = len(dre_rows) > 0
        present_in_master = hunt_code in hunt_master_codes
        present_in_reference = hunt_code in hunt_reference_codes
        reason_not_modeled = ""
        recommended_action = ""
        if bucket == "in_database_not_modeled":
            reason_not_modeled, recommended_action = _pick_reason_for_unmodeled(
                hunt_code=hunt_code,
                ml_rows=ml_rows,
                coverage_by_code=coverage_by_code,
                present_in_hunt_master=present_in_master,
                present_in_hunt_reference=present_in_reference,
            )

        if bucket == "modeled_not_in_database" and not reason_not_modeled:
            reason_not_modeled = "RETIRED_OR_RENAMED_HUNT_CODE"
            recommended_action = "Confirm whether the modeled code is a renamed or retired code that should remain history-only."
        if bucket == "coverage_seen_not_in_database" and not reason_not_modeled:
            reason_not_modeled = "OBSERVED_HISTORY_ONLY"
            recommended_action = "Keep in coverage history unless a current canonical mapping is restored."
        if bucket == "historical_or_observed_only" and not reason_not_modeled:
            reason_not_modeled = "OBSERVED_HISTORY_ONLY"
            recommended_action = "Historical/observed-only code; do not force into active modeled predictions."
        if bucket == "pending_or_non_probability_status" and not reason_not_modeled:
            reason_not_modeled = "IN_SCOPE_MODEL_PENDING"
            recommended_action = "In scope but pending/non-probability strategy; keep out of draw-odds modeled totals."
        if bucket == "out_of_scope_or_excluded" and not reason_not_modeled:
            reason_not_modeled = "OUT_OF_SCOPE_NON_TARGET"
            recommended_action = "Out-of-scope/excluded category; retain in audit coverage only."

        rows.append(
            {
                "bucket": bucket,
                "hunt_code": hunt_code,
                "hunt_name": hunt_name,
                "species": species,
                "permit_type": permit_type,
                "draw_system_type": "|".join(draw_types),
                "algorithm_status": "|".join(statuses),
                "present_in_ml_draw_predictions_v1": "YES" if present_in_ml else "NO",
                "present_in_draw_reality_engine_predictive_v2": "YES" if present_in_dre else "NO",
                "present_in_hunt_master_enriched": "YES" if present_in_master else "NO",
                "present_in_hunt_unit_reference_linked": "YES" if present_in_reference else "NO",
                "reason_not_modeled": reason_not_modeled,
                "recommended_action": recommended_action,
            }
        )
    return rows


def build_database_hunt_code_model_gap_report(
    output_dir: Path,
    forecast_year: int = 2026,
    history_years: list[int] | None = None,
    expected_database_count: int = 1294,
) -> dict[str, Path]:
    history_years = history_years or [2021, 2022, 2023, 2024, 2025]
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical_path, canonical_rows, canonical_candidate_counts, selection_note = _choose_canonical_database_file(
        expected_count=expected_database_count
    )
    ml_path = REPO / "processed_data" / "ml_draw_predictions_v1.csv"
    dre_predictive_path = REPO / "processed_data" / "draw_reality_engine_predictive_v2.csv"
    coverage_json_path = REPO / "processed_data" / "draw_system_coverage_report.json"
    coverage_csv_path = REPO / "processed_data" / "draw_system_coverage_report.csv"
    hunt_master_path = REPO / "processed_data" / "hunt_master_enriched.csv"
    hunt_reference_path = REPO / "processed_data" / "hunt_unit_reference_linked.csv"

    ml_rows = _read_csv(ml_path)
    dre_rows = _read_csv(dre_predictive_path)
    coverage_rows = _read_csv(coverage_csv_path)
    coverage_report = json.loads(coverage_json_path.read_text(encoding="utf-8"))
    hunt_master_rows = _read_csv(hunt_master_path)
    hunt_reference_rows = _read_csv(hunt_reference_path)

    db_codes = {_code(row.get("hunt_code")) for row in canonical_rows if _clean(row.get("hunt_code"))}
    ml_codes = {_code(row.get("hunt_code")) for row in ml_rows if _clean(row.get("hunt_code"))}
    dre_codes = {_code(row.get("hunt_code")) for row in dre_rows if _clean(row.get("hunt_code"))}
    hunt_master_codes = {_code(row.get("hunt_code")) for row in hunt_master_rows if _clean(row.get("hunt_code"))}
    hunt_reference_codes = {_code(row.get("hunt_code")) for row in hunt_reference_rows if _clean(row.get("hunt_code"))}
    coverage_codes_all = {_code(row.get("hunt_code")) for row in coverage_rows if _clean(row.get("hunt_code"))}
    coverage_target_scope_codes = {
        _code(row.get("hunt_code"))
        for row in coverage_rows
        if _clean(row.get("hunt_code")) and _clean(row.get("target_scope")) == "TARGET"
    }
    coverage_predictive_codes = {
        _code(row.get("hunt_code"))
        for row in coverage_rows
        if _clean(row.get("hunt_code")) and _clean(row.get("source_dataset")) == "predictive"
    }
    coverage_observed_codes = {
        _code(row.get("hunt_code"))
        for row in coverage_rows
        if _clean(row.get("hunt_code")) and _clean(row.get("source_dataset")) == "observed_runtime"
    }
    modeled_target_codes = {
        _code(row.get("hunt_code"))
        for row in coverage_rows
        if _clean(row.get("hunt_code"))
        and _clean(row.get("source_dataset")) == "predictive"
        and _clean(row.get("modeled_by_engine")) == "True"
        and _clean(row.get("target_scope")) == "TARGET"
    }
    draw_odds_modeled_codes = {
        _code(row.get("hunt_code"))
        for row in ml_rows
        if _clean(row.get("hunt_code"))
        and _clean(row.get("algorithm_status")) in DRAW_ODDS_MODELED_STATUSES
    }

    ml_rows_by_code = _by_hunt_code(ml_rows)
    dre_rows_by_code = _by_hunt_code(dre_rows)
    db_rows_by_code = _by_hunt_code(canonical_rows)
    coverage_by_code = _by_hunt_code(coverage_rows)

    in_database_and_modeled = db_codes & modeled_target_codes
    in_database_not_modeled = db_codes - modeled_target_codes
    modeled_not_in_database = modeled_target_codes - db_codes
    coverage_seen_not_in_database = coverage_target_scope_codes - db_codes
    historical_or_observed_only = (coverage_observed_codes - coverage_predictive_codes) & coverage_codes_all

    pending_or_non_probability_status_codes = {
        _code(row.get("hunt_code"))
        for row in ml_rows
        if _clean(row.get("hunt_code")) and _clean(row.get("algorithm_status")) in PENDING_OR_NON_PROBABILITY_STATUSES
    }
    out_of_scope_or_excluded_codes = {
        _code(row.get("hunt_code"))
        for row in ml_rows
        if _clean(row.get("hunt_code"))
        and _clean(row.get("algorithm_status")) in {"OUT_OF_SCOPE_NON_TARGET", "EXCLUDED_NOT_PREDICTIVE_DRAW"}
    }

    bucket_rows: list[dict[str, object]] = []
    bucket_rows.extend(
        _bucket_rows(
            "in_database_not_modeled",
            in_database_not_modeled,
            db_rows_by_code,
            ml_rows_by_code,
            dre_rows_by_code,
            hunt_master_codes,
            hunt_reference_codes,
            coverage_by_code,
        )
    )
    bucket_rows.extend(
        _bucket_rows(
            "in_database_and_modeled",
            in_database_and_modeled,
            db_rows_by_code,
            ml_rows_by_code,
            dre_rows_by_code,
            hunt_master_codes,
            hunt_reference_codes,
            coverage_by_code,
        )
    )
    bucket_rows.extend(
        _bucket_rows(
            "modeled_not_in_database",
            modeled_not_in_database,
            db_rows_by_code,
            ml_rows_by_code,
            dre_rows_by_code,
            hunt_master_codes,
            hunt_reference_codes,
            coverage_by_code,
        )
    )
    bucket_rows.extend(
        _bucket_rows(
            "coverage_seen_not_in_database",
            coverage_seen_not_in_database,
            db_rows_by_code,
            ml_rows_by_code,
            dre_rows_by_code,
            hunt_master_codes,
            hunt_reference_codes,
            coverage_by_code,
        )
    )
    bucket_rows.extend(
        _bucket_rows(
            "historical_or_observed_only",
            historical_or_observed_only,
            db_rows_by_code,
            ml_rows_by_code,
            dre_rows_by_code,
            hunt_master_codes,
            hunt_reference_codes,
            coverage_by_code,
        )
    )
    bucket_rows.extend(
        _bucket_rows(
            "pending_or_non_probability_status",
            pending_or_non_probability_status_codes,
            db_rows_by_code,
            ml_rows_by_code,
            dre_rows_by_code,
            hunt_master_codes,
            hunt_reference_codes,
            coverage_by_code,
        )
    )
    bucket_rows.extend(
        _bucket_rows(
            "out_of_scope_or_excluded",
            out_of_scope_or_excluded_codes,
            db_rows_by_code,
            ml_rows_by_code,
            dre_rows_by_code,
            hunt_master_codes,
            hunt_reference_codes,
            coverage_by_code,
        )
    )

    reason_counter = Counter(
        row["reason_not_modeled"] for row in bucket_rows if row["bucket"] == "in_database_not_modeled" and row["reason_not_modeled"]
    )
    database_not_modeled_detail = [row for row in bucket_rows if row["bucket"] == "in_database_not_modeled"]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "forecast_year": forecast_year,
        "source_years": history_years,
        "canonical_database_file": _safe_relative(canonical_path),
        "canonical_database_selection_note": selection_note,
        "canonical_database_candidate_counts": canonical_candidate_counts,
        "expected_database_unique_hunt_code_count_reference": expected_database_count,
        "database_unique_hunt_code_count": len(db_codes),
        "database_count_matches_expected_1294": len(db_codes) == expected_database_count,
        "database_count_explanation": (
            "Database unique hunt-code count matches the expected 1,294 reference."
            if len(db_codes) == expected_database_count
            else (
                "No canonical database candidate in the current repo produced 1,294 unique hunt codes; "
                f"selected canonical source reports {len(db_codes)} unique hunt codes."
            )
        ),
        "modeled_target_hunt_code_count": int(coverage_report.get("modeled_target_hunt_codes", len(modeled_target_codes))),
        "database_to_modeled_gap_count": len(db_codes) - int(coverage_report.get("modeled_target_hunt_codes", len(modeled_target_codes))),
        "coverage_target_scope_hunt_code_count": int(coverage_report.get("target_scope_hunt_codes", len(coverage_target_scope_codes))),
        "coverage_to_database_overage_count": int(coverage_report.get("target_scope_hunt_codes", len(coverage_target_scope_codes))) - len(db_codes),
        "in_database_and_modeled_count": len(in_database_and_modeled),
        "in_database_not_modeled_count": len(in_database_not_modeled),
        "modeled_not_in_database_count": len(modeled_not_in_database),
        "coverage_seen_not_in_database_count": len(coverage_seen_not_in_database),
        "active_predictive_hunt_code_count": len(ml_codes),
        "observed_history_only_hunt_code_count": len(historical_or_observed_only),
        "pending_hunt_code_count": len(
            {
                _code(row.get("hunt_code"))
                for row in ml_rows
                if _clean(row.get("hunt_code")) and _clean(row.get("algorithm_status")) == "IN_SCOPE_MODEL_PENDING"
            }
        ),
        "out_of_scope_hunt_code_count": len(
            {
                _code(row.get("hunt_code"))
                for row in ml_rows
                if _clean(row.get("hunt_code")) and _clean(row.get("algorithm_status")) == "OUT_OF_SCOPE_NON_TARGET"
            }
        ),
        "excluded_not_predictive_draw_hunt_code_count": len(
            {
                _code(row.get("hunt_code"))
                for row in ml_rows
                if _clean(row.get("hunt_code")) and _clean(row.get("algorithm_status")) == "EXCLUDED_NOT_PREDICTIVE_DRAW"
            }
        ),
        "bucket_counts": {
            "in_database_and_modeled": len(in_database_and_modeled),
            "in_database_not_modeled": len(in_database_not_modeled),
            "modeled_not_in_database": len(modeled_not_in_database),
            "coverage_seen_not_in_database": len(coverage_seen_not_in_database),
            "historical_or_observed_only": len(historical_or_observed_only),
            "pending_or_non_probability_status": len(pending_or_non_probability_status_codes),
            "out_of_scope_or_excluded": len(out_of_scope_or_excluded_codes),
        },
        "top_gap_reasons": dict(reason_counter.most_common(15)),
        "requires_classifier_mapping_count": int(reason_counter.get("NEEDS_CLASSIFIER_MAPPING", 0)),
        "requires_strategy_implementation_count": int(reason_counter.get("NEEDS_STRATEGY_IMPLEMENTATION", 0)),
        "correctly_not_modeled_count": int(
            sum(
                reason_counter.get(key, 0)
                for key in (
                    "IN_SCOPE_MODEL_PENDING",
                    "MODELED_ALLOCATION_NOT_DRAW_ODDS",
                    "MODELED_AVAILABILITY_NOT_DRAW_ODDS",
                    "EXCLUDED_NOT_PREDICTIVE_DRAW",
                    "OUT_OF_SCOPE_NON_TARGET",
                    "OBSERVED_HISTORY_ONLY",
                )
            )
        ),
        "draw_odds_modeled_hunt_code_count": len(draw_odds_modeled_codes),
        "draw_odds_modeled_statuses": sorted(DRAW_ODDS_MODELED_STATUSES),
        "database_not_modeled_detail": database_not_modeled_detail,
        "modeled_not_in_database_hunt_codes": sorted(modeled_not_in_database),
        "coverage_seen_not_in_database_hunt_codes": sorted(coverage_seen_not_in_database),
        "historical_or_observed_only_hunt_codes": sorted(historical_or_observed_only),
        "source_files": {
            "canonical_database": _safe_relative(canonical_path),
            "ml_draw_predictions_v1": _safe_relative(ml_path),
            "draw_reality_engine_predictive_v2": _safe_relative(dre_predictive_path),
            "draw_system_coverage_report_json": _safe_relative(coverage_json_path),
            "draw_system_coverage_report_csv": _safe_relative(coverage_csv_path),
            "hunt_master_enriched": _safe_relative(hunt_master_path),
            "hunt_unit_reference_linked": _safe_relative(hunt_reference_path),
        },
    }

    csv_path = output_dir / "database_hunt_code_model_gap.csv"
    json_path = output_dir / "database_hunt_code_model_gap.json"
    md_path = output_dir / "database_hunt_code_model_gap.md"

    csv_rows = sorted(bucket_rows, key=lambda row: (str(row.get("bucket")), str(row.get("hunt_code"))))
    _write_csv(
        csv_path,
        csv_rows,
        [
            "bucket",
            "hunt_code",
            "hunt_name",
            "species",
            "permit_type",
            "draw_system_type",
            "algorithm_status",
            "present_in_ml_draw_predictions_v1",
            "present_in_draw_reality_engine_predictive_v2",
            "present_in_hunt_master_enriched",
            "present_in_hunt_unit_reference_linked",
            "reason_not_modeled",
            "recommended_action",
        ],
    )
    _write_json(json_path, report)

    md_lines = [
        "# Database Hunt-Code Model Gap Audit",
        "",
        "## Summary",
        "",
        f"- Canonical database file used: `{report['canonical_database_file']}`",
        f"- Database unique hunt-code count: `{report['database_unique_hunt_code_count']}`",
        f"- Modeled target hunt-code count: `{report['modeled_target_hunt_code_count']}`",
        f"- Database-to-modeled gap count: `{report['database_to_modeled_gap_count']}`",
        f"- Coverage target-scope hunt-code count: `{report['coverage_target_scope_hunt_code_count']}`",
        f"- Coverage-to-database overage count: `{report['coverage_to_database_overage_count']}`",
        "",
        "## Bucket Counts",
        "",
    ]
    for bucket, count in report["bucket_counts"].items():
        md_lines.append(f"- `{bucket}`: `{count}`")
    md_lines.extend(
        [
            "",
            "## Top Gap Reasons",
            "",
        ]
    )
    for reason, count in reason_counter.most_common(15):
        md_lines.append(f"- `{reason}`: `{count}`")
    md_lines.extend(
        [
            "",
            "## Count Note",
            "",
            f"- {report['database_count_explanation']}",
        ]
    )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {"csv": csv_path, "json": json_path, "md": md_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO / "processed_data"))
    parser.add_argument("--forecast-year", type=int, default=2026)
    parser.add_argument("--history-years", default="2021,2022,2023,2024,2025")
    parser.add_argument("--expected-database-count", type=int, default=1294)
    args = parser.parse_args()
    history_years = [int(token.strip()) for token in str(args.history_years).split(",") if token.strip()]
    artifacts = build_database_hunt_code_model_gap_report(
        output_dir=Path(args.output_dir),
        forecast_year=args.forecast_year,
        history_years=history_years,
        expected_database_count=args.expected_database_count,
    )
    print(json.dumps({key: str(value) for key, value in artifacts.items()}, indent=2))


if __name__ == "__main__":
    main()
