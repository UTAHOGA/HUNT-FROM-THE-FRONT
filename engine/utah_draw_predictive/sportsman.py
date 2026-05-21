"""Phase 8 sportsman permit predictive helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Mapping

from . import (
    ALGORITHM_STATUS_MODELED_SPORTSMAN_DRAW,
    StrategySpec,
    TARGET_SCOPE_TARGET,
)


MODEL_STRATEGY_NAME = "SPORTSMAN_DRAW"
SPORTSMAN_DRAW_SYSTEM_TYPE = "SPORTSMAN_PERMIT"
SPORTSMAN_SOURCE_TOKEN = "SPORTSMAN_PERMIT"
SPORTSMAN_SOURCE_NO_ODDS_TOKEN = "SPORTSMAN_PERMIT_NO_DRAW_ODDS"

KNOWN_SPORTSMAN_CODES = {
    "BI1000": "Bison",
    "BR1000": "Black Bear",
    "CG9999": "Cougar",
    "DB0007": "Deer",
    "DS1000": "Desert Bighorn Sheep",
    "EB1000": "Elk",
    "GO1000": "Mountain Goat",
    "MB1000": "Moose",
    "PB1000": "Pronghorn",
    "RS0001": "Rocky Mountain Bighorn Sheep",
    "TK0001": "Turkey",
}

SPORTSMAN_CODE_ALIASES = {
    "DB0007": [],
}

STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type=SPORTSMAN_DRAW_SYSTEM_TYPE,
        module_name="engine.utah_draw_predictive.sportsman",
        algorithm_status=ALGORITHM_STATUS_MODELED_SPORTSMAN_DRAW,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Sportsman permits use their own statewide-draw strategy and only promote rows when a usable official sportsman odds source exists.",
        modeled_by_engine=True,
        legacy_logic_present=True,
    )
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
        for key in ("hunt_code", "hunt_name", "species", "hunt_type", "hunt_class", "weapon", "draw_pool", "source_file")
    )


def is_sportsman_permit_row(row: Mapping[str, object]) -> bool:
    hunt_code = _clean(row.get("hunt_code")).upper()
    text = _joined_text(row)
    if SPORTSMAN_SOURCE_TOKEN.lower() in text:
        return True
    if "sportsman" in text:
        return True
    if hunt_code in KNOWN_SPORTSMAN_CODES:
        return True
    return any(hunt_code in aliases for aliases in SPORTSMAN_CODE_ALIASES.values())


def sportsman_species(row: Mapping[str, object]) -> str:
    hunt_code = _clean(row.get("hunt_code")).upper()
    return _clean(row.get("species")) or KNOWN_SPORTSMAN_CODES.get(hunt_code, "")


def is_modeled_sportsman_row(row: Mapping[str, object]) -> bool:
    return (
        _clean(row.get("draw_system_type")) == SPORTSMAN_DRAW_SYSTEM_TYPE
        and _clean_lower(row.get("model_strategy")) == MODEL_STRATEGY_NAME.lower()
        and _clean_lower(row.get("sportsman_valid")) in {"1", "true", "yes", "y"}
    )


def _usable_sportsman_truth_rows(truth_rows: Iterable[Mapping[str, object]], history_years: set[int]) -> dict[tuple[str, str], dict[str, object]]:
    usable: dict[tuple[str, str], dict[str, object]] = {}
    for row in truth_rows:
        if not is_sportsman_permit_row(row):
            continue
        year = _to_int(row.get("year"))
        if year not in history_years:
            continue
        source_file = _clean_lower(row.get("source_file"))
        if SPORTSMAN_SOURCE_NO_ODDS_TOKEN.lower() in source_file:
            continue
        residency = _clean(row.get("residency")) or "Resident"
        applicants = _to_int(row.get("eligible_applicants"))
        permits = _to_int(row.get("total_permits"))
        if applicants <= 0 or permits <= 0:
            continue
        hunt_code = _clean(row.get("hunt_code")).upper()
        denominator = applicants
        probability = min(1.0, max(0.0, permits / max(applicants, 1)))
        usable[(hunt_code, residency)] = {
            "sportsman_permit_count": permits,
            "sportsman_applicants": applicants,
            "sportsman_odds_denominator": denominator,
            "sportsman_odds_text": f"{permits} in {denominator}",
            "p_sportsman_draw": probability,
            "source_file": _clean(row.get("source_file")),
        }
    return usable


def build_sportsman_predictions(
    truth_rows: Iterable[Mapping[str, object]],
    db_rows: Iterable[Mapping[str, object]],
    forecast_year: int,
    history_years: list[int],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    history_year_set = {int(year) for year in history_years}
    usable_truth = _usable_sportsman_truth_rows(truth_rows, history_year_set)
    truth_rows_seen = [row for row in truth_rows if is_sportsman_permit_row(row)]
    rows: list[dict[str, object]] = []
    source_files_used: set[str] = set()
    code_aliases: dict[str, list[str]] = defaultdict(list)

    for db_row in db_rows:
        if not is_sportsman_permit_row(db_row):
            continue
        hunt_code = _clean(db_row.get("hunt_code")).upper()
        hunt_name = _clean(db_row.get("hunt_name"))
        species = sportsman_species(db_row)
        for residency in ("Resident", "Nonresident"):
            source_years_used = ",".join(str(year) for year in history_years)
            row = {
                "year": str(forecast_year),
                "forecast_year": str(forecast_year),
                "hunt_code": hunt_code,
                "hunt_name": hunt_name,
                "species": species,
                "sportsman_species": species,
                "sex_type": _clean(db_row.get("sex_type")),
                "hunt_type": _clean(db_row.get("hunt_type")) or "Statewide",
                "hunt_class": _clean(db_row.get("hunt_class")) or "Public",
                "residency": residency,
                "points": "",
                "draw_pool": "standard",
                "sportsman_permit_count": "",
                "sportsman_applicants": "",
                "sportsman_odds_text": "",
                "sportsman_odds_denominator": "",
                "p_sportsman_draw": "",
                "p_draw": "",
                "p_draw_pct": "",
                "p_bonus_pool": "",
                "p_random_pool": "",
                "p_preference_draw": "",
                "source_years_used": source_years_used,
                "source_year_count": len(history_years),
                "latest_source_year": max(history_years),
                "earliest_source_year": min(history_years),
                "source_dataset": "predictive",
                "model_strategy": MODEL_STRATEGY_NAME,
                "draw_system_type": SPORTSMAN_DRAW_SYSTEM_TYPE,
                "sportsman_valid": "FALSE",
                "sportsman_model_note": "SPORTSMAN ODDS SOURCE MISSING",
                "draw_outlook": "SPORTSMAN ODDS SOURCE MISSING",
            }
            modeled = usable_truth.get((hunt_code, residency))
            if modeled:
                probability = float(modeled["p_sportsman_draw"])
                row.update(
                    {
                        "sportsman_permit_count": str(modeled["sportsman_permit_count"]),
                        "sportsman_applicants": str(modeled["sportsman_applicants"]),
                        "sportsman_odds_text": modeled["sportsman_odds_text"],
                        "sportsman_odds_denominator": str(modeled["sportsman_odds_denominator"]),
                        "p_sportsman_draw": f"{probability:.6f}",
                        "p_draw": f"{probability:.6f}",
                        "p_draw_pct": f"{probability * 100.0:.3f}",
                        "sportsman_valid": "TRUE",
                        "sportsman_model_note": "Modeled from official sportsman odds source.",
                        "draw_outlook": "STATEWIDE DRAW",
                    }
                )
                source_files_used.add(str(modeled["source_file"]))
            rows.append(row)
        if hunt_code in SPORTSMAN_CODE_ALIASES:
            code_aliases[hunt_code] = list(SPORTSMAN_CODE_ALIASES[hunt_code])

    modeled_rows = [row for row in rows if _clean(row.get("sportsman_valid")) == "TRUE"]
    pending_rows = [row for row in rows if _clean(row.get("sportsman_valid")) != "TRUE"]
    report = {
        "forecast_year": forecast_year,
        "source_years": history_years,
        "sportsman_rows_reviewed": len(rows),
        "sportsman_rows_modeled": len(modeled_rows),
        "sportsman_rows_pending": len(pending_rows),
        "sportsman_species_list": sorted({row.get("sportsman_species", "") for row in rows if _clean(row.get("sportsman_species"))}),
        "sportsman_hunt_codes": sorted({row.get("hunt_code", "") for row in rows if _clean(row.get("hunt_code"))}),
        "sportsman_code_aliases": {key: value for key, value in sorted(code_aliases.items()) if value},
        "sportsman_permit_count": sum(_to_int(row.get("sportsman_permit_count")) for row in rows),
        "sportsman_applicant_count": sum(_to_int(row.get("sportsman_applicants")) for row in rows),
        "p_sportsman_draw_non_null_count": sum(1 for row in rows if _clean(row.get("p_sportsman_draw"))),
        "p_draw_non_null_count": sum(1 for row in rows if _clean(row.get("p_draw"))),
        "p_draw_pct_non_null_count": sum(1 for row in rows if _clean(row.get("p_draw_pct"))),
        "p_bonus_pool_non_null_count": 0,
        "p_random_pool_non_null_count": 0,
        "p_preference_draw_non_null_count": 0,
        "rows_with_p_draw_outside_range": sum(1 for row in rows if _clean(row.get("p_draw")) and not (0.0 <= float(str(row.get("p_draw"))) <= 1.0)),
        "rows_with_p_draw_pct_outside_range": sum(1 for row in rows if _clean(row.get("p_draw_pct")) and not (0.0 <= float(str(row.get("p_draw_pct"))) <= 100.0)),
        "duplicate_key_count": len(rows) - len({(row.get("hunt_code", ""), row.get("residency", ""), row.get("points", "")) for row in rows}),
        "source_files_used": sorted(source_files_used),
        "source_years_used_non_null_count": sum(1 for row in rows if _clean(row.get("source_years_used"))),
    }
    return rows, report
