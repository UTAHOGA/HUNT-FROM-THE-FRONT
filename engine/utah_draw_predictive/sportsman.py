"""Phase 11 sportsman permit predictive helpers."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping

from . import (
    ALGORITHM_STATUS_MODELED_SPORTSMAN_DRAW,
    StrategySpec,
    TARGET_SCOPE_TARGET,
)


MODEL_STRATEGY_NAME = "SPORTSMAN_DRAW"
SPORTSMAN_DRAW_SYSTEM_TYPE = "SPORTSMAN_PERMIT"
SPORTSMAN_SOURCE_YEAR = 2025

REPO = Path(__file__).resolve().parents[2]
SPORTSMAN_SOURCE_CSV = REPO / "data" / "utah" / "sportsman" / "sportsman_odds_2025.csv"
SPORTSMAN_SOURCE_XLSX = REPO / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "xlsx" / "24-25_sportsman_odds.xlsx"

SPORTSMAN_CODE_ALIASES: dict[str, list[str]] = {
    "BI1000": [],
    "BR1000": [],
    "DB0007": [],
    "DS1000": [],
    "EB1000": [],
    "GO1000": [],
    "MB1000": [],
    "PB1000": [],
    "RS0001": [],
    "TK0001": [],
}

STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type=SPORTSMAN_DRAW_SYSTEM_TYPE,
        module_name="engine.utah_draw_predictive.sportsman",
        algorithm_status=ALGORITHM_STATUS_MODELED_SPORTSMAN_DRAW,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Sportsman permits use their own official statewide-odds source and do not inherit bonus or preference mechanics.",
        modeled_by_engine=True,
        legacy_logic_present=True,
    )
]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _clean_lower(value: object) -> str:
    return _clean(value).lower()


def _safe_int(value: object) -> int:
    text = _clean(value).replace(",", "")
    if not text or text.upper() == "N/A":
        return 0
    try:
        return int(float(text))
    except Exception:
        return 0


def _safe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


@lru_cache(maxsize=1)
def _read_sportsman_source_rows() -> tuple[dict[str, str], ...]:
    with SPORTSMAN_SOURCE_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


@lru_cache(maxsize=1)
def _sportsman_source_by_code() -> dict[str, dict[str, str]]:
    return {
        _clean(row.get("hunt_code")).upper(): row
        for row in _read_sportsman_source_rows()
        if _clean(row.get("hunt_code"))
    }


@lru_cache(maxsize=1)
def sportsman_code_allowlist() -> set[str]:
    codes = set(_sportsman_source_by_code().keys())
    for aliases in SPORTSMAN_CODE_ALIASES.values():
        codes.update(_clean(alias).upper() for alias in aliases if _clean(alias))
    return codes


def _joined_text(row: Mapping[str, object]) -> str:
    return " ".join(
        _clean_lower(row.get(key))
        for key in (
            "hunt_code",
            "hunt_name",
            "permit_name",
            "species",
            "hunt_type",
            "hunt_class",
            "weapon",
            "draw_pool",
            "sportsman_species",
        )
    )


def _canonical_sportsman_code(row: Mapping[str, object]) -> str:
    hunt_code = _clean(row.get("hunt_code")).upper()
    if hunt_code in _sportsman_source_by_code():
        return hunt_code
    for canonical_code, aliases in SPORTSMAN_CODE_ALIASES.items():
        if hunt_code in {_clean(alias).upper() for alias in aliases if _clean(alias)}:
            return canonical_code
    return hunt_code


def is_sportsman_permit_row(row: Mapping[str, object]) -> bool:
    hunt_code = _canonical_sportsman_code(row)
    text = _joined_text(row)
    if hunt_code in _sportsman_source_by_code():
        return True
    if "sportsman" in text:
        return True
    return False


def sportsman_species(row: Mapping[str, object]) -> str:
    canonical_code = _canonical_sportsman_code(row)
    source_row = _sportsman_source_by_code().get(canonical_code, {})
    return _clean(source_row.get("species")) or _clean(row.get("species"))


def is_modeled_sportsman_row(row: Mapping[str, object]) -> bool:
    return (
        _clean(row.get("draw_system_type")) == SPORTSMAN_DRAW_SYSTEM_TYPE
        and _clean_lower(row.get("model_strategy")) == MODEL_STRATEGY_NAME.lower()
        and _clean_lower(row.get("sportsman_valid")) in {"1", "true", "yes", "y"}
        and _clean(row.get("residency")).lower() == "resident"
        and _clean(row.get("p_sportsman_draw")) != ""
    )


def build_sportsman_predictions(
    truth_rows: Iterable[Mapping[str, object]],
    db_rows: Iterable[Mapping[str, object]],
    forecast_year: int,
    history_years: list[int],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    del truth_rows

    sportsman_source = _sportsman_source_by_code()
    db_by_code = {
        _clean(row.get("hunt_code")).upper(): dict(row)
        for row in db_rows
        if _clean(row.get("hunt_code"))
    }
    rows: list[dict[str, object]] = []

    for hunt_code in sorted(sportsman_source.keys()):
        source_row = sportsman_source[hunt_code]
        db_row = db_by_code.get(hunt_code, {})
        resident_quota = _safe_int(source_row.get("resident_quota"))
        denominator = _safe_int(source_row.get("odds_denominator")) or _safe_int(source_row.get("resident_apps")) or _safe_int(source_row.get("total_apps"))
        probability = 0.0 if denominator <= 0 else min(1.0, max(0.0, resident_quota / denominator))
        hunt_name = _clean(source_row.get("hunt_name")) or _clean(db_row.get("hunt_name"))
        season = _clean(db_row.get("season"))
        row = {
            "year": str(forecast_year),
            "forecast_year": str(forecast_year),
            "hunt_code": hunt_code,
            "hunt_name": hunt_name,
            "species": _clean(source_row.get("species")) or _clean(db_row.get("species")),
            "sportsman_species": _clean(source_row.get("species")) or _clean(db_row.get("species")),
            "sex_type": _clean(db_row.get("sex_type")),
            "hunt_type": "Sportsman Permit",
            "hunt_class": "Public",
            "residency": "Resident",
            "points": "",
            "draw_pool": "sportsman",
            "sportsman_source_year": str(SPORTSMAN_SOURCE_YEAR),
            "sportsman_permit_count": str(resident_quota),
            "sportsman_applicants": str(_safe_int(source_row.get("resident_apps"))),
            "sportsman_odds_text": _clean(source_row.get("odds_text")),
            "sportsman_odds_denominator": str(denominator),
            "p_sportsman_draw": f"{probability:.6f}",
            "p_draw": f"{probability:.6f}",
            "p_draw_pct": f"{probability * 100.0:.3f}",
            "p_bonus_pool": "",
            "p_random_pool": "",
            "p_preference_draw": "",
            "source_years_used": str(SPORTSMAN_SOURCE_YEAR),
            "source_year_count": 1,
            "latest_source_year": SPORTSMAN_SOURCE_YEAR,
            "earliest_source_year": SPORTSMAN_SOURCE_YEAR,
            "source_dataset": "predictive",
            "model_strategy": MODEL_STRATEGY_NAME,
            "draw_system_type": SPORTSMAN_DRAW_SYSTEM_TYPE,
            "sportsman_valid": "TRUE",
            "sportsman_model_note": "Modeled from official Sportsman odds source.",
            "draw_outlook": "STATEWIDE DRAW",
            "sportsman_residency_scope": "RESIDENT_ONLY",
            "sportsman_source_file": _safe_relative(SPORTSMAN_SOURCE_CSV),
            "season_dates": season,
            "weapon": _clean(db_row.get("weapon")),
        }
        rows.append(row)

    report = {
        "forecast_year": forecast_year,
        "source_years": history_years,
        "sportsman_source_year": SPORTSMAN_SOURCE_YEAR,
        "sportsman_rows_reviewed": len(rows),
        "total_sportsman_rows_reviewed": len(rows),
        "sportsman_rows_modeled": len(rows),
        "modeled_sportsman_rows": len(rows),
        "sportsman_rows_pending": 0,
        "pending_sportsman_rows": 0,
        "hunt_code_list": [row["hunt_code"] for row in rows],
        "sportsman_hunt_codes": [row["hunt_code"] for row in rows],
        "species_list": [row["sportsman_species"] for row in rows],
        "sportsman_species_list": [row["sportsman_species"] for row in rows],
        "p_sportsman_draw_non_null_count": sum(1 for row in rows if _clean(row.get("p_sportsman_draw"))),
        "p_draw_non_null_count": sum(1 for row in rows if _clean(row.get("p_draw"))),
        "p_draw_pct_non_null_count": sum(1 for row in rows if _clean(row.get("p_draw_pct"))),
        "p_bonus_pool_non_null_count": 0,
        "p_random_pool_non_null_count": 0,
        "p_preference_draw_non_null_count": 0,
        "duplicate_key_count": len(rows) - len({(row["hunt_code"], row["residency"], row["points"]) for row in rows}),
        "source_files_used": [
            _safe_relative(SPORTSMAN_SOURCE_CSV),
            _safe_relative(SPORTSMAN_SOURCE_XLSX),
        ],
    }
    return rows, report
