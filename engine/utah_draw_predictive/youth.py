"""Youth general deer and youth any-bull elk strategy helpers."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping

from engine.utah_bonus_predictive.rules import MODEL_VERSION

from . import ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING, StrategySpec, TARGET_SCOPE_TARGET


REPO = Path(__file__).resolve().parents[2]

YOUTH_GENERAL_DEER_DRAW_SYSTEM_TYPE = "YOUTH_GENERAL_DEER"
YOUTH_GENERAL_ANY_BULL_ELK_DRAW_SYSTEM_TYPE = "YOUTH_GENERAL_ANY_BULL_ELK"
YOUTH_DRAW_SYSTEM_TYPES = {
    YOUTH_GENERAL_DEER_DRAW_SYSTEM_TYPE,
    YOUTH_GENERAL_ANY_BULL_ELK_DRAW_SYSTEM_TYPE,
}

YOUTH_DEER_MODEL_STRATEGY_NAME = "youth_general_deer_pending_phase15"
YOUTH_ELK_MODEL_STRATEGY_NAME = "youth_general_any_bull_elk_pending_phase15"
RULE_VERSION = "utah_youth_strategy_phase15_v1.0.0"

YOUTH_ELK_SOURCE_PATH = REPO / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "2026_elk_general_anybull_youth.csv"

YOUTH_DEER_SOURCE_FILES = {
    "21_youth_deer.pdf",
    "22_youth_deer.pdf",
    "2025 youth g.s. deer draw results.pdf",
}
YOUTH_ELK_SOURCE_FILES = {
    "20_youth_bull_elk.pdf",
    "21_youth_bull_elk.pdf",
    "22_youth_bull_elk.pdf",
    "24_youth_elk.pdf",
    "2025 youth g.s.. mature bull draw.pdf",
}


STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type="GENERAL_BIG_GAME_OTHER",
        module_name="engine.utah_draw_predictive.youth",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="This target-scope big-game draw category is not yet assigned to an accepted production strategy.",
        legacy_logic_present=True,
    ),
    StrategySpec(
        draw_system_type=YOUTH_GENERAL_DEER_DRAW_SYSTEM_TYPE,
        module_name="engine.utah_draw_predictive.youth",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Youth general deer is in scope but stays separate from the adult general-season buck deer model until the active-year youth pool is source-proven.",
        legacy_logic_present=True,
    ),
    StrategySpec(
        draw_system_type=YOUTH_GENERAL_ANY_BULL_ELK_DRAW_SYSTEM_TYPE,
        module_name="engine.utah_draw_predictive.youth",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Youth general any-bull elk is in scope but remains pending until the current-year mechanics and quota surface support a defensible strategy.",
        legacy_logic_present=True,
    ),
]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _clean_lower(value: object) -> str:
    return _clean(value).lower()


def _to_int(value: object) -> int:
    text = _clean(value).replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except Exception:
        return 0


def _joined_text(row: Mapping[str, object]) -> str:
    return " ".join(
        _clean_lower(row.get(key))
        for key in (
            "hunt_code",
            "hunt_name",
            "species",
            "sex_type",
            "hunt_type",
            "hunt_class",
            "weapon",
            "draw_pool",
            "source_file",
            "NOTES",
            "notes",
        )
    )


def _source_file_name(row: Mapping[str, object]) -> str:
    raw = _clean(row.get("source_file"))
    if not raw:
        return ""
    return Path(raw).name.lower()


def is_youth_general_deer_row(row: Mapping[str, object]) -> bool:
    text = _joined_text(row)
    if "deer" not in text or "antlerless" in text or "doe" in text or "dedicated hunter" in text:
        return False
    source_name = _source_file_name(row)
    draw_pool = _clean_lower(row.get("draw_pool"))
    if source_name in YOUTH_DEER_SOURCE_FILES:
        return True
    if "youth" in text and any(token in text for token in ("general season", "general-season", "extended archery", "hunters choice", "hunters choice")):
        return True
    if draw_pool == "youth" and any(token in text for token in ("general season", "general-season", "extended archery")):
        return True
    return False


def is_youth_general_any_bull_elk_row(row: Mapping[str, object]) -> bool:
    text = _joined_text(row)
    if "elk" not in text or "antlerless" in text:
        return False
    source_name = _source_file_name(row)
    draw_pool = _clean_lower(row.get("draw_pool"))
    hunt_code = _clean(row.get("hunt_code")).upper()
    if source_name in YOUTH_ELK_SOURCE_FILES:
        return True
    if hunt_code == "EB1011" and "youth" in text:
        return True
    if "youth" in text and any(token in text for token in ("any bull", "any-bull", "bull elk", "hunters choice", "hunters choice", "general season - youth")):
        return True
    if draw_pool in {"youth", "youth_mature_bull"}:
        return True
    return False


def resolve_youth_algorithm_status(row: Mapping[str, object], draw_system_type: str) -> str:
    existing = _clean(row.get("algorithm_status"))
    if existing:
        return existing
    if draw_system_type in YOUTH_DRAW_SYSTEM_TYPES:
        return ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING
    return existing


def build_youth_predictions(
    truth_rows: Iterable[Mapping[str, object]],
    db_rows: Iterable[Mapping[str, object]],
    forecast_year: int,
    history_years: list[int],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    youth_deer_history = [dict(row) for row in truth_rows if is_youth_general_deer_row(row)]
    youth_elk_history = [dict(row) for row in truth_rows if is_youth_general_any_bull_elk_row(row)]

    source_files_used: set[str] = {_clean(row.get("source_file")) for row in youth_deer_history + youth_elk_history if _clean(row.get("source_file"))}
    data_quality_counter: Counter[str] = Counter()
    rows: list[dict[str, object]] = []

    deer_predictive_rows = [dict(row) for row in db_rows if is_youth_general_deer_row(row)]
    if not deer_predictive_rows:
        data_quality_counter["YOUTH_DEER_ACTIVE_2026_SOURCE_MISSING_OR_SHARED_POOL_AMBIGUOUS"] += 1

    youth_elk_source_rows: dict[str, dict[str, str]] = {}
    if YOUTH_ELK_SOURCE_PATH.exists():
        with YOUTH_ELK_SOURCE_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                hunt_code = _clean(row.get("hunt_code")).upper()
                if hunt_code:
                    youth_elk_source_rows[hunt_code] = dict(row)
        source_files_used.add(str(YOUTH_ELK_SOURCE_PATH.relative_to(REPO)))

    elk_predictive_candidates = [dict(row) for row in db_rows if is_youth_general_any_bull_elk_row(row)]
    elk_by_code: dict[str, dict[str, str]] = {}
    for row in elk_predictive_candidates:
        hunt_code = _clean(row.get("hunt_code")).upper()
        if hunt_code and hunt_code not in elk_by_code:
            elk_by_code[hunt_code] = row

    for hunt_code, db_row in sorted(elk_by_code.items()):
        source_row = youth_elk_source_rows.get(hunt_code, {})
        season_dates = _clean(source_row.get("season")) or _clean(db_row.get("season"))
        weapon = _clean(source_row.get("weapon")) or _clean(db_row.get("weapon"))
        permits_total = _to_int(source_row.get("permits_2026_total")) or _to_int(db_row.get("permits_2026_total"))
        flags = ["YOUTH_ELK_MODEL_PENDING"]
        if permits_total <= 0:
            flags.append("YOUTH_ELK_QUOTA_NOT_PUBLISHED")
        flags.append("YOUTH_ELK_MECHANICS_NOT_CONFIRMED")
        for flag in flags:
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
                    "species": _clean(db_row.get("species")) or "Elk",
                    "sex_type": _clean(db_row.get("sex_type")) or "Bull",
                    "hunt_type": _clean(db_row.get("hunt_type")) or "General Season - Youth",
                    "hunt_class": _clean(db_row.get("hunt_class")) or "Public",
                    "residency": residency,
                    "points": "",
                    "draw_pool": "youth",
                    "public_permits_2025": "",
                    "public_permits_2026": str(permits_total) if permits_total > 0 else "",
                    "source_years_used": ",".join(str(year) for year in history_years),
                    "source_year_count": len(history_years),
                    "latest_source_year": max(history_years),
                    "earliest_source_year": min(history_years),
                    "source_dataset": "predictive",
                    "model_strategy": YOUTH_ELK_MODEL_STRATEGY_NAME,
                    "weapon": weapon,
                    "season_dates": season_dates,
                    "season_status": "SEASON DATES PRESENT" if season_dates else "SEASON DATES MISSING",
                    "draw_system_type": YOUTH_GENERAL_ANY_BULL_ELK_DRAW_SYSTEM_TYPE,
                    "algorithm_status": ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
                    "draw_outlook": "MODEL PENDING",
                    "availability_status": "",
                    "p_availability": "",
                    "availability_pct": "",
                    "permit_type": "Youth General Any-Bull Elk",
                    "permit_status": "",
                    "rule_status": "",
                    "data_quality_flags": "|".join(flags),
                    "p_draw": "",
                    "p_draw_pct": "",
                    "p_preference_draw": "",
                    "p_bonus_pool": "",
                    "p_bonus_pool_pct": "",
                    "p_random_pool": "",
                    "p_random_pool_pct": "",
                }
            )

    youth_rows = rows
    modeled_preference_rows = [row for row in youth_rows if _clean(row.get("algorithm_status")) == "MODELED_PREFERENCE"]
    modeled_allocation_rows = [row for row in youth_rows if _clean(row.get("algorithm_status")) == "MODELED_ALLOCATION"]
    modeled_availability_rows = [row for row in youth_rows if _clean(row.get("algorithm_status")) == "MODELED_AVAILABILITY"]
    pending_rows = [row for row in youth_rows if _clean(row.get("algorithm_status")) == ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING]
    excluded_rows = [row for row in youth_rows if _clean(row.get("algorithm_status")) == "EXCLUDED_NOT_PREDICTIVE_DRAW"]

    report = {
        "forecast_year": forecast_year,
        "source_years": history_years,
        "total_youth_rows_reviewed": len(youth_deer_history) + len(youth_elk_history) + len(deer_predictive_rows) + len(elk_predictive_candidates),
        "youth_general_deer_rows_reviewed": len(youth_deer_history) + len(deer_predictive_rows),
        "youth_general_any_bull_elk_rows_reviewed": len(youth_elk_history) + len(elk_predictive_candidates),
        "active_predictive_youth_row_count": len(youth_rows),
        "youth_general_deer_row_count": len([row for row in youth_rows if row.get("draw_system_type") == YOUTH_GENERAL_DEER_DRAW_SYSTEM_TYPE]),
        "youth_general_any_bull_elk_row_count": len([row for row in youth_rows if row.get("draw_system_type") == YOUTH_GENERAL_ANY_BULL_ELK_DRAW_SYSTEM_TYPE]),
        "youth_hunt_code_count": len({row.get("hunt_code", "") for row in youth_rows if _clean(row.get("hunt_code"))}),
        "rows_by_algorithm_status": {
            "MODELED_PREFERENCE": len(modeled_preference_rows),
            "MODELED_ALLOCATION": len(modeled_allocation_rows),
            "MODELED_AVAILABILITY": len(modeled_availability_rows),
            "IN_SCOPE_MODEL_PENDING": len(pending_rows),
            "EXCLUDED_NOT_PREDICTIVE_DRAW": len(excluded_rows),
        },
        "modeled_preference_row_count": len(modeled_preference_rows),
        "modeled_allocation_row_count": len(modeled_allocation_rows),
        "modeled_availability_row_count": len(modeled_availability_rows),
        "in_scope_model_pending_row_count": len(pending_rows),
        "excluded_not_predictive_draw_row_count": len(excluded_rows),
        "p_draw_non_null_count": sum(1 for row in youth_rows if _clean(row.get("p_draw"))),
        "p_draw_pct_non_null_count": sum(1 for row in youth_rows if _clean(row.get("p_draw_pct"))),
        "p_preference_draw_non_null_count": sum(1 for row in youth_rows if _clean(row.get("p_preference_draw"))),
        "p_bonus_pool_non_null_count": sum(1 for row in youth_rows if _clean(row.get("p_bonus_pool"))),
        "p_random_pool_non_null_count": sum(1 for row in youth_rows if _clean(row.get("p_random_pool"))),
        "p_availability_non_null_count": sum(1 for row in youth_rows if _clean(row.get("p_availability"))),
        "availability_pct_non_null_count": sum(1 for row in youth_rows if _clean(row.get("availability_pct"))),
        "p_draw_outside_0_1_count": 0,
        "p_draw_pct_outside_0_100_count": 0,
        "duplicate_key_count": len(youth_rows) - len({(row.get("hunt_code", ""), row.get("residency", ""), row.get("points", "")) for row in youth_rows}),
        "source_files_used": sorted(source_files_used),
        "data_quality_flags_summary": dict(sorted(data_quality_counter.items())),
    }
    return rows, report
