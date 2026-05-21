"""Phase 9 private-lands-only antlerless elk allocation helpers."""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping

from engine.utah_bonus_predictive.rules import MODEL_VERSION

from . import (
    ALGORITHM_STATUS_MODELED_ALLOCATION,
    StrategySpec,
    TARGET_SCOPE_TARGET,
)


MODEL_STRATEGY_NAME = "private_lands_antlerless_elk_allocation_phase9"
RULE_VERSION = "utah_private_lands_antlerless_elk_allocation_v1.0.0"
DRAW_SYSTEM_TYPE = "PRIVATE_LANDS_ONLY_ANTLERLESS_ELK"

PRIVATE_LANDS_TOKENS = (
    "private lands only",
    "private land only",
    "private-land-only",
    "private lands antlerless elk",
    "private land antlerless elk",
    "antlerless elk private lands only",
    " plo ",
)

STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type=DRAW_SYSTEM_TYPE,
        module_name="engine.utah_draw_predictive.private_lands_antlerless_elk",
        algorithm_status=ALGORITHM_STATUS_MODELED_ALLOCATION,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Private-lands-only antlerless elk uses an allocation/availability strategy, not preference or bonus draw odds.",
        modeled_by_engine=True,
        legacy_logic_present=True,
    ),
]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _clean_lower(value: object) -> str:
    return _clean(value).lower()


def _to_int(value: object) -> int:
    text = _clean(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except Exception:
        return 0


def _joined_text(row: Mapping[str, object]) -> str:
    return " ".join(
        _clean_lower(row.get(key))
        for key in ("hunt_code", "hunt_name", "species", "sex_type", "hunt_type", "hunt_class", "weapon", "NOTES", "notes", "source_file")
    )


def is_private_lands_antlerless_elk_row(row: Mapping[str, object]) -> bool:
    text = _joined_text(row)
    return (
        "elk" in text
        and ("antlerless" in text or _clean_lower(row.get("sex_type")) in {"antlerless", "cow", "cow only"})
        and any(token in f" {text} " for token in PRIVATE_LANDS_TOKENS)
    )


def is_modeled_private_lands_antlerless_elk_row(row: Mapping[str, object]) -> bool:
    return (
        _clean(row.get("draw_system_type")) == DRAW_SYSTEM_TYPE
        and _clean_lower(row.get("model_strategy")) == MODEL_STRATEGY_NAME
        and _clean_lower(row.get("private_lands_allocation_valid")) in {"1", "true", "yes", "y"}
    )


def build_private_lands_antlerless_elk_predictions(
    truth_rows: Iterable[Mapping[str, object]],
    db_rows: Iterable[Mapping[str, object]],
    forecast_year: int,
    history_years: list[int],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    truth_by_code: dict[str, dict[str, str]] = {}
    source_files: set[str] = set()
    for row in truth_rows:
        if not is_private_lands_antlerless_elk_row(row):
            continue
        hunt_code = _clean(row.get("hunt_code")).upper()
        if not hunt_code:
            continue
        truth_by_code.setdefault(
            hunt_code,
            {
                "season_dates": _clean(row.get("season")),
                "unit": _clean(row.get("unit")) or _clean(row.get("hunt_name")),
                "source_file": _clean(row.get("source_file")),
            },
        )
        if _clean(row.get("source_file")):
            source_files.add(_clean(row.get("source_file")))

    rows: list[dict[str, object]] = []
    data_quality_counter: Counter[str] = Counter()
    reviewed_rows: list[dict[str, object]] = []

    for db_row in db_rows:
        if not is_private_lands_antlerless_elk_row(db_row):
            continue
        reviewed_rows.append(dict(db_row))
        hunt_code = _clean(db_row.get("hunt_code")).upper()
        if not hunt_code:
            continue
        permits_allotted = _to_int(db_row.get("permits_2026_total"))
        truth_meta = truth_by_code.get(hunt_code, {})
        season_dates = _clean(truth_meta.get("season_dates")) or _clean(db_row.get("season"))
        unit = _clean(truth_meta.get("unit")) or _clean(db_row.get("hunt_name"))
        source_file = _clean(truth_meta.get("source_file")) or "DATABASE.csv"
        source_files.add(source_file)

        algorithm_status = "MODELED_ALLOCATION" if permits_allotted > 0 else "IN_SCOPE_MODEL_PENDING"
        allocation_status = "ALLOCATION KNOWN / REMAINING UNKNOWN" if permits_allotted > 0 else "SOURCE MISSING"
        data_quality_flags = []
        if permits_allotted > 0:
            data_quality_flags.extend(["REMAINING_PERMIT_STATUS_UNKNOWN", "ALLOCATION_NOT_RESIDENCY_SPLIT"])
        else:
            data_quality_flags.append("SOURCE_MISSING")
        for flag in data_quality_flags:
            data_quality_counter[flag] += 1

        for residency in ("Resident", "Nonresident"):
            rows.append(
                {
                    "model_version": MODEL_VERSION,
                    "rule_version": RULE_VERSION,
                    "year": str(forecast_year),
                    "forecast_year": str(forecast_year),
                    "hunt_code": hunt_code,
                    "hunt_name": _clean(db_row.get("hunt_name")),
                    "species": _clean(db_row.get("species")),
                    "sex_type": _clean(db_row.get("sex_type")),
                    "hunt_type": _clean(db_row.get("hunt_type")),
                    "hunt_class": "Public",
                    "residency": residency,
                    "points": "",
                    "draw_pool": "standard",
                    "source_dataset": "predictive",
                    "source_years_used": ",".join(str(year) for year in history_years),
                    "source_year_count": len(history_years),
                    "latest_source_year": max(history_years),
                    "earliest_source_year": min(history_years),
                    "model_strategy": MODEL_STRATEGY_NAME,
                    "weapon": _clean(db_row.get("weapon")),
                    "draw_system_type": DRAW_SYSTEM_TYPE,
                    "private_lands_allocation_valid": "TRUE" if permits_allotted > 0 else "FALSE",
                    "private_lands_allocation_note": allocation_status,
                    "permits_allotted": str(permits_allotted) if permits_allotted > 0 else "",
                    "permits_remaining": "",
                    "permits_sold": "",
                    "allocation_status": allocation_status,
                    "p_availability": "",
                    "availability_pct": "",
                    "sellout_risk": "",
                    "closure_risk": "",
                    "sale_date": "",
                    "unit": unit,
                    "season_dates": season_dates,
                    "private_land_only_flag": "TRUE",
                    "data_quality_flags": "|".join(data_quality_flags),
                    "p_draw": "",
                    "p_draw_pct": "",
                    "p_bonus_pool": "",
                    "p_bonus_pool_pct": "",
                    "p_random_pool": "",
                    "p_random_pool_pct": "",
                    "p_preference_draw": "",
                }
            )

    modeled_rows = [row for row in rows if _clean(row.get("private_lands_allocation_valid")) == "TRUE"]
    pending_rows = [row for row in rows if _clean(row.get("private_lands_allocation_valid")) != "TRUE"]
    report = {
        "forecast_year": forecast_year,
        "source_years": history_years,
        "total_private_lands_antlerless_elk_rows_reviewed": len(reviewed_rows),
        "modeled_allocation_row_count": len(modeled_rows),
        "pending_allocation_row_count": len(pending_rows),
        "excluded_row_count": 0,
        "hunt_code_count": len({row.get("hunt_code", "") for row in rows if _clean(row.get("hunt_code"))}),
        "unit_count": len({row.get("unit", "") for row in rows if _clean(row.get("unit"))}),
        "permits_allotted_non_null_count": sum(1 for row in rows if _clean(row.get("permits_allotted"))),
        "permits_remaining_non_null_count": sum(1 for row in rows if _clean(row.get("permits_remaining"))),
        "p_availability_non_null_count": sum(1 for row in rows if _clean(row.get("p_availability"))),
        "availability_pct_non_null_count": sum(1 for row in rows if _clean(row.get("availability_pct"))),
        "p_draw_non_null_count": 0,
        "p_draw_pct_non_null_count": 0,
        "p_bonus_pool_non_null_count": 0,
        "p_random_pool_non_null_count": 0,
        "p_preference_draw_non_null_count": 0,
        "rows_with_availability_pct_outside_range": 0,
        "duplicate_key_count": len(rows) - len({(row.get("hunt_code", ""), row.get("residency", ""), row.get("points", "")) for row in rows}),
        "source_files_used": sorted(source_files),
        "data_quality_flags_summary": dict(sorted(data_quality_counter.items())),
    }
    return rows, report
