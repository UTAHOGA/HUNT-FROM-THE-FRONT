"""Phase 7 turkey bonus predictive helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from typing import Iterable, Mapping

from engine.utah_bonus_predictive.monte_carlo import combine_probabilities, compute_bonus_pool_probability
from engine.utah_bonus_predictive.rules import MODEL_VERSION
from engine.utah_bonus_predictive.split import split_utah_bonus_permits

from . import ALGORITHM_STATUS_MODELED_BONUS, StrategySpec, TARGET_SCOPE_TARGET


MODEL_STRATEGY_NAME = "turkey_bonus_phase7"
TURKEY_RULE_VERSION = "utah_turkey_bonus_v1.0.0"
TURKEY_DRAW_SYSTEM_TYPE = "BONUS_TURKEY"


STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type=TURKEY_DRAW_SYSTEM_TYPE,
        module_name="engine.utah_draw_predictive.turkey",
        algorithm_status=ALGORITHM_STATUS_MODELED_BONUS,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Limited-entry turkey uses the Utah bonus model and only promotes rows with proven limited-entry public-draw source data, valid quota, and modeled bonus probabilities.",
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


def _round_count(value: float) -> int:
    return max(0, int(round(value)))


def _band_for_points(points: int) -> str:
    if points <= 0:
        return "0"
    if points == 1:
        return "1"
    if points <= 3:
        return "2_3"
    if points <= 5:
        return "4_5"
    if points <= 9:
        return "6_9"
    return "10_plus"


def _joined_text(row: Mapping[str, object]) -> str:
    return " ".join(
        _clean_lower(row.get(key))
        for key in ("hunt_code", "hunt_name", "species", "sex_type", "hunt_type", "hunt_class", "weapon", "draw_pool")
    )


def is_turkey_row(row: Mapping[str, object]) -> bool:
    return "turkey" in _joined_text(row)


def is_general_season_turkey_row(row: Mapping[str, object]) -> bool:
    if not is_turkey_row(row):
        return False
    text = _joined_text(row)
    hunt_type = _clean_lower(row.get("hunt_type"))
    return "spring general season" in text or hunt_type == "statewide"


def is_remaining_turkey_row(row: Mapping[str, object]) -> bool:
    if not is_turkey_row(row):
        return False
    text = _joined_text(row)
    return any(token in text for token in ("remaining permit", "remaining", "over the counter", " otc", "first-come", "first come"))


def is_nonpublic_turkey_row(row: Mapping[str, object]) -> bool:
    if not is_turkey_row(row):
        return False
    text = _joined_text(row)
    return any(token in text for token in ("private", "landowner", "voucher", "sportsman", "conservation", "expo"))


def is_fall_management_turkey_row(row: Mapping[str, object]) -> bool:
    return is_turkey_row(row) and "fall management" in _joined_text(row)


def is_supported_turkey_bonus_row(row: Mapping[str, object]) -> bool:
    if not is_turkey_row(row):
        return False
    if is_general_season_turkey_row(row) or is_remaining_turkey_row(row) or is_nonpublic_turkey_row(row) or is_fall_management_turkey_row(row):
        return False
    hunt_type = _clean_lower(row.get("hunt_type"))
    hunt_class = _clean_lower(row.get("hunt_class"))
    draw_pool = _clean_lower(row.get("draw_pool"))
    if draw_pool == "youth_turkey" or hunt_class == "youth":
        return False
    if hunt_type == "limited entry":
        return hunt_class in {"", "public"} and draw_pool in {"", "standard"}
    if hunt_type == "cwmu":
        return hunt_class in {"", "cwmu"} and draw_pool in {"", "standard"}
    return False


def is_modeled_turkey_row(row: Mapping[str, object]) -> bool:
    return (
        _clean_lower(row.get("model_strategy")) == MODEL_STRATEGY_NAME
        and _clean_lower(row.get("turkey_bonus_valid")) in {"1", "true", "yes", "y"}
        and _clean(row.get("draw_system_type")) == TURKEY_DRAW_SYSTEM_TYPE
    )


def _build_truth_ladders(
    truth_rows: Iterable[Mapping[str, object]],
    history_years: set[int],
) -> tuple[
    dict[tuple[int, str, str], dict[int, dict[str, int]]],
    dict[str, dict[str, str]],
    dict[tuple[str, int], dict[str, int]],
]:
    ladders: dict[tuple[int, str, str], dict[int, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"eligible": 0, "bonus": 0, "regular": 0, "total": 0})
    )
    meta: dict[str, dict[str, str]] = {}
    total_drawn_by_code_year: dict[tuple[str, int], dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in truth_rows:
        year = _to_int(row.get("year"))
        if year not in history_years:
            continue
        if not is_supported_turkey_bonus_row(row):
            continue

        hunt_code = _clean(row.get("hunt_code")).upper()
        residency = _clean(row.get("residency")) or "Resident"
        points = _to_int(row.get("points"))
        eligible = _to_int(row.get("eligible_applicants"))
        bonus = _to_int(row.get("bonus_permits"))
        regular = _to_int(row.get("regular_permits"))
        total = _to_int(row.get("total_permits"))

        if not hunt_code:
            continue

        ladders[(year, hunt_code, residency)][points]["eligible"] += eligible
        ladders[(year, hunt_code, residency)][points]["bonus"] += bonus
        ladders[(year, hunt_code, residency)][points]["regular"] += regular
        ladders[(year, hunt_code, residency)][points]["total"] += total
        total_drawn_by_code_year[(hunt_code, year)][residency] += total

        if hunt_code not in meta:
            meta[hunt_code] = {
                "hunt_name": _clean(row.get("hunt_name")),
                "species": _clean(row.get("species")),
                "hunt_type": _clean(row.get("hunt_type")),
                "hunt_class": _clean(row.get("hunt_class")),
                "weapon": _clean(row.get("weapon")),
                "sex_type": _clean(row.get("sex_type")),
            }

    return ladders, meta, total_drawn_by_code_year


def _build_retention_and_zero_growth(
    ladders: Mapping[tuple[int, str, str], dict[int, dict[str, int]]],
) -> tuple[dict[str, float], float]:
    retention_samples: dict[str, list[float]] = defaultdict(list)
    zero_growth_samples: list[float] = []
    years_by_key: dict[tuple[str, str], list[int]] = defaultdict(list)
    for year, hunt_code, residency in ladders:
        years_by_key[(hunt_code, residency)].append(year)

    for (hunt_code, residency), years in years_by_key.items():
        for prior_year in sorted(years):
            next_year = prior_year + 1
            if next_year not in years:
                continue
            prior = ladders[(prior_year, hunt_code, residency)]
            nxt = ladders[(next_year, hunt_code, residency)]
            prior_zero = prior.get(0, {}).get("eligible", 0)
            next_zero = nxt.get(0, {}).get("eligible", 0)
            if prior_zero > 0:
                zero_growth_samples.append(max(0.25, min(2.0, next_zero / prior_zero)))
            for points, values in prior.items():
                unsuccessful = max(values["eligible"] - values["bonus"] - values["regular"], 0)
                if unsuccessful <= 0:
                    continue
                band = _band_for_points(points)
                next_count = nxt.get(points + 1, {}).get("eligible", 0)
                retention_samples[band].append(max(0.0, min(1.25, next_count / unsuccessful)))

    default_retention = {
        "0": 0.78,
        "1": 0.84,
        "2_3": 0.89,
        "4_5": 0.92,
        "6_9": 0.95,
        "10_plus": 0.98,
    }
    retention_by_band: dict[str, float] = {}
    for band, fallback in default_retention.items():
        samples = retention_samples.get(band, [])
        retention_by_band[band] = round(mean(samples), 4) if samples else fallback
    zero_growth = round(mean(zero_growth_samples), 4) if zero_growth_samples else 1.0
    return retention_by_band, zero_growth


def _forecast_applicant_ladder(
    latest_ladder: Mapping[int, dict[str, int]],
    retention_by_band: Mapping[str, float],
    zero_growth: float,
) -> dict[int, int]:
    prior_points = sorted(int(points) for points in latest_ladder.keys())
    max_points = max(prior_points) if prior_points else 0
    forecast: dict[int, int] = {}
    forecast[0] = _round_count(latest_ladder.get(0, {}).get("eligible", 0) * zero_growth)

    for points in range(1, max_points + 2):
        prior_level = latest_ladder.get(points - 1, {})
        unsuccessful_prior = max(int(prior_level.get("eligible", 0)) - int(prior_level.get("bonus", 0)) - int(prior_level.get("regular", 0)), 0)
        retained = unsuccessful_prior * retention_by_band.get(_band_for_points(points - 1), 0.86)
        switch_proxy = int(latest_ladder.get(points, {}).get("eligible", 0)) * 0.08
        forecast[points] = _round_count(retained + switch_proxy)

    while forecast and forecast.get(max(forecast.keys()), 0) == 0:
        forecast.pop(max(forecast.keys()))
    return forecast


def _weighted_random_probability(points: int, applicants_by_points: Mapping[int, int], random_permits: int) -> float:
    total_weight = 0.0
    target_weight = 0.0
    for point_level, count in applicants_by_points.items():
        weight = max(0, int(count)) * max(1, int(point_level) + 1)
        total_weight += weight
        if int(point_level) == int(points):
            target_weight += weight
    if random_permits <= 0 or total_weight <= 0 or target_weight <= 0:
        return 0.0
    share = min(1.0, max(0.0, target_weight / total_weight))
    return max(0.0, min(1.0, 1.0 - ((1.0 - share) ** max(1, random_permits))))


def _guaranteed_level(ladder: Mapping[int, int], quota: int) -> int | None:
    running = 0
    guaranteed: int | None = None
    for points in sorted(ladder.keys(), reverse=True):
        applicants = max(int(ladder.get(points, 0)), 0)
        if applicants <= 0:
            continue
        if running + applicants <= quota:
            guaranteed = points
            running += applicants
            continue
        break
    return guaranteed


def _status(max_point_permits: int, random_permits: int, p_bonus_pool: float) -> str:
    if max_point_permits == 0 and random_permits > 0:
        return "RANDOM ONLY"
    if p_bonus_pool >= 0.999:
        return "MAX POOL"
    if p_bonus_pool > 0:
        return "ON EDGE"
    return "BEHIND"


def _draw_outlook(probability: float, gap: int | None, pending: bool = False, excluded: bool = False) -> str:
    if excluded:
        return "NOT A DRAW"
    if pending:
        return "MODEL PENDING"
    if probability >= 0.75:
        return "GREEN LIGHT"
    if probability >= 0.10 or (gap is not None and gap <= 1):
        return "MAY DRAW IN 5-10 YEARS"
    return "RANDOM POOL RELIANCE" if probability > 0 else "POINT CREEP DEFEAT"


def _trend(prior_level: int | None, forecast_level: int | None) -> str:
    if prior_level is None and forecast_level is None:
        return "YELLOW"
    if prior_level is None:
        return "GREEN"
    if forecast_level is None:
        return "RED"
    if forecast_level > prior_level:
        return "GREEN"
    if forecast_level == prior_level:
        return "YELLOW"
    return "RED"


def _forecast_quota_for_residency(
    hunt_code: str,
    residency: str,
    forecast_total: int,
    latest_year: int,
    total_drawn_by_code_year: Mapping[tuple[str, int], dict[str, int]],
) -> int:
    observed = total_drawn_by_code_year.get((hunt_code, latest_year), {})
    observed_total = sum(int(value) for value in observed.values())
    if forecast_total <= 0:
        return 0
    if observed_total <= 0:
        return forecast_total if residency == "Resident" else 0
    resident_drawn = int(observed.get("Resident", 0))
    resident_quota = max(0, min(forecast_total, round(forecast_total * (resident_drawn / max(observed_total, 1)))))
    return resident_quota if residency == "Resident" else max(0, forecast_total - resident_quota)


def _data_quality_flags(total_applicants: int, public_quota: int, max_point_permits: int, available_years: list[int]) -> list[str]:
    flags: list[str] = []
    if len(available_years) < 2:
        flags.append("MISSING_MULTIPLE_YEARS")
    if total_applicants < 5:
        flags.append("LOW_APPLICANT_COUNT")
    if public_quota == 1:
        flags.append("ONE_PERMIT_RANDOM_ONLY")
    if max_point_permits == 0 and public_quota > 0:
        flags.append("NO_MAX_POINT_POOL")
    return flags


def build_turkey_bonus_predictions(
    truth_rows: Iterable[Mapping[str, object]],
    db_rows: Iterable[Mapping[str, object]],
    forecast_year: int,
    history_years: list[int],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    history_year_set = set(int(year) for year in history_years)
    latest_source_year = max(history_year_set)
    source_years_used_text = ",".join(str(year) for year in history_years)
    source_year_count = len(history_years)
    earliest_source_year = min(history_years)
    ladders, meta, total_drawn_by_code_year = _build_truth_ladders(truth_rows, history_year_set)
    retention_by_band, zero_growth = _build_retention_and_zero_growth(ladders)

    rows: list[dict[str, object]] = []
    data_quality_counter: Counter[str] = Counter()
    reviewed_turkey_rows = 0
    excluded_general_season_rows = 0
    excluded_remaining_rows = 0
    excluded_non_public_rows = 0
    excluded_other_rows = 0

    current_codes: dict[str, dict[str, object]] = {}
    for row in db_rows:
        if not is_turkey_row(row):
            continue
        reviewed_turkey_rows += 1
        if is_general_season_turkey_row(row):
            excluded_general_season_rows += 1
            continue
        if is_remaining_turkey_row(row):
            excluded_remaining_rows += 1
            continue
        if is_nonpublic_turkey_row(row):
            excluded_non_public_rows += 1
            continue
        if is_fall_management_turkey_row(row):
            excluded_other_rows += 1
            continue
        if not is_supported_turkey_bonus_row(row):
            excluded_other_rows += 1
            continue
        hunt_code = _clean(row.get("hunt_code")).upper()
        if hunt_code:
            current_codes[hunt_code] = dict(row)

    years_by_key: dict[tuple[str, str], list[int]] = defaultdict(list)
    for year, hunt_code, residency in ladders:
        years_by_key[(hunt_code, residency)].append(year)

    for hunt_code, db_row in sorted(current_codes.items()):
        forecast_total = _to_int(db_row.get("permits_2026_total"))
        hunt_name = _clean(db_row.get("hunt_name")) or meta.get(hunt_code, {}).get("hunt_name", "")
        species = _clean(db_row.get("species")) or meta.get(hunt_code, {}).get("species", "Turkey")
        hunt_type = _clean(db_row.get("hunt_type")) or meta.get(hunt_code, {}).get("hunt_type", "")
        hunt_class = _clean(db_row.get("hunt_class")) or meta.get(hunt_code, {}).get("hunt_class", "")
        weapon = _clean(db_row.get("weapon")) or meta.get(hunt_code, {}).get("weapon", "")
        sex_type = _clean(db_row.get("sex_type")) or meta.get(hunt_code, {}).get("sex_type", "")

        for residency in ("Resident", "Nonresident"):
            available_years = sorted(year for year in set(years_by_key.get((hunt_code, residency), [])) if year in history_year_set)
            latest_available_year = max(available_years) if available_years else None
            forecast_quota = _forecast_quota_for_residency(hunt_code, residency, forecast_total, latest_available_year or latest_source_year, total_drawn_by_code_year)
            latest_ladder = ladders.get((latest_available_year or latest_source_year, hunt_code, residency), {})
            prior_total = sum(int(values.get("total", 0)) for values in latest_ladder.values())
            row_source_years_used = ",".join(str(year) for year in available_years) if available_years else source_years_used_text
            row_source_year_count = len(available_years) if available_years else source_year_count
            row_latest_source_year = latest_available_year or latest_source_year
            row_earliest_source_year = min(available_years) if available_years else earliest_source_year

            if not available_years or forecast_quota <= 0:
                rows.append(
                    {
                        "model_version": MODEL_VERSION,
                        "rule_version": TURKEY_RULE_VERSION,
                        "year": str(forecast_year),
                        "forecast_year": str(forecast_year),
                        "hunt_code": hunt_code,
                        "hunt_name": hunt_name,
                        "species": species,
                        "sex_type": sex_type,
                        "hunt_type": hunt_type,
                        "hunt_class": hunt_class or ("CWMU" if _clean_lower(db_row.get("hunt_type")) == "cwmu" else "Public"),
                        "residency": residency,
                        "points": "",
                        "draw_pool": "standard",
                        "public_permits_2025": prior_total,
                        "public_permits_2026": forecast_quota,
                        "p_preference_draw": "",
                        "p_bonus_pool": "",
                        "p_random_pool": "",
                        "p_draw": "",
                        "p_draw_pct": "",
                        "draw_outlook": "MODEL PENDING",
                        "source_years_used": row_source_years_used,
                        "source_year_count": row_source_year_count,
                        "latest_source_year": row_latest_source_year,
                        "earliest_source_year": row_earliest_source_year,
                        "source_dataset": "predictive",
                        "model_strategy": MODEL_STRATEGY_NAME,
                        "turkey_bonus_valid": "FALSE",
                        "turkey_bonus_note": "Missing latest turkey source year, multiple-year history, or usable forecast quota.",
                        "weapon": weapon,
                        "draw_system_type": TURKEY_DRAW_SYSTEM_TYPE,
                        "data_quality_flags": "|".join(
                            flag
                            for flag in [
                                "MISSING_PRIOR_YEAR" if not available_years else "",
                                "MISSING_MULTIPLE_YEARS" if len(available_years) < 2 else "",
                                "MISSING_FORECAST_QUOTA" if forecast_quota <= 0 else "",
                            ]
                            if flag
                        ),
                    }
                )
                continue

            forecast_ladder = _forecast_applicant_ladder(latest_ladder, retention_by_band, zero_growth)
            if not forecast_ladder:
                rows.append(
                    {
                        "model_version": MODEL_VERSION,
                        "rule_version": TURKEY_RULE_VERSION,
                        "year": str(forecast_year),
                        "forecast_year": str(forecast_year),
                        "hunt_code": hunt_code,
                        "hunt_name": hunt_name,
                        "species": species,
                        "sex_type": sex_type,
                        "hunt_type": hunt_type,
                        "hunt_class": hunt_class or ("CWMU" if _clean_lower(db_row.get("hunt_type")) == "cwmu" else "Public"),
                        "residency": residency,
                        "points": "",
                        "draw_pool": "standard",
                        "public_permits_2025": prior_total,
                        "public_permits_2026": forecast_quota,
                        "p_preference_draw": "",
                        "p_bonus_pool": "",
                        "p_random_pool": "",
                        "p_draw": "",
                        "p_draw_pct": "",
                        "draw_outlook": "MODEL PENDING",
                        "source_years_used": row_source_years_used,
                        "source_year_count": row_source_year_count,
                        "latest_source_year": row_latest_source_year,
                        "earliest_source_year": row_earliest_source_year,
                        "source_dataset": "predictive",
                        "model_strategy": MODEL_STRATEGY_NAME,
                        "turkey_bonus_valid": "FALSE",
                        "turkey_bonus_note": "No forecast turkey applicant ladder could be built.",
                        "weapon": weapon,
                        "draw_system_type": TURKEY_DRAW_SYSTEM_TYPE,
                        "data_quality_flags": "LOW_APPLICANT_COUNT",
                    }
                )
                continue

            split = split_utah_bonus_permits(forecast_quota)
            max_point_permits = split.maxPointPermits
            random_permits = split.randomPermits
            prior_guaranteed = _guaranteed_level({points: int(values.get("eligible", 0)) for points, values in latest_ladder.items()}, prior_total)
            forecast_guaranteed = _guaranteed_level(forecast_ladder, forecast_quota)
            total_applicants = sum(forecast_ladder.values())
            flags = _data_quality_flags(total_applicants, forecast_quota, max_point_permits, available_years)
            for flag in flags:
                data_quality_counter[flag] += 1

            for points in sorted(forecast_ladder.keys(), reverse=True):
                applicants_by_points = {int(level): int(count) for level, count in forecast_ladder.items()}
                p_bonus_pool, applicants_above, applicants_at_level = compute_bonus_pool_probability(points, applicants_by_points, max_point_permits)
                p_random_pool = _weighted_random_probability(points, applicants_by_points, random_permits)
                p_draw = combine_probabilities(p_bonus_pool, p_random_pool)
                gap = (forecast_guaranteed - points) if forecast_guaranteed is not None else None
                prior_gap = (prior_guaranteed - points) if prior_guaranteed is not None else None
                delta_gap = None if gap is None or prior_gap is None else gap - prior_gap

                rows.append(
                    {
                        "model_version": MODEL_VERSION,
                        "rule_version": TURKEY_RULE_VERSION,
                        "year": str(forecast_year),
                        "forecast_year": str(forecast_year),
                        "hunt_code": hunt_code,
                        "hunt_name": hunt_name,
                        "species": species,
                        "sex_type": sex_type,
                        "hunt_type": hunt_type,
                        "hunt_class": hunt_class or ("CWMU" if _clean_lower(db_row.get("hunt_type")) == "cwmu" else "Public"),
                        "residency": residency,
                        "points": str(points),
                        "draw_pool": "standard",
                        "public_permits_2025": prior_total,
                        "public_permits_2026": forecast_quota,
                        "max_point_permits_2025": "",
                        "max_point_permits_2026": max_point_permits,
                        "random_permits_2025": "",
                        "random_permits_2026": random_permits,
                        "guaranteed_at_2025": "" if prior_guaranteed is None else str(prior_guaranteed),
                        "guaranteed_at_2026": "" if forecast_guaranteed is None else str(forecast_guaranteed),
                        "applicants_above": applicants_above,
                        "applicants_at_level": applicants_at_level,
                        "p_preference_draw": "",
                        "p_bonus_pool": f"{p_bonus_pool:.6f}",
                        "p_random_pool": f"{p_random_pool:.6f}",
                        "p_draw": f"{p_draw:.6f}",
                        "p_bonus_pool_pct": f"{p_bonus_pool * 100.0:.3f}",
                        "p_random_pool_pct": f"{p_random_pool * 100.0:.3f}",
                        "p_draw_pct": f"{p_draw * 100.0:.3f}",
                        "random_draw_odds_2026": f"{p_random_pool * 100.0:.3f}",
                        "gap": "" if gap is None else str(gap),
                        "delta_gap": "" if delta_gap is None else str(delta_gap),
                        "status": _status(max_point_permits, random_permits, p_bonus_pool),
                        "trend": _trend(prior_guaranteed, forecast_guaranteed),
                        "draw_outlook": _draw_outlook(p_draw, gap),
                        "source_years_used": row_source_years_used,
                        "source_year_count": row_source_year_count,
                        "latest_source_year": row_latest_source_year,
                        "earliest_source_year": row_earliest_source_year,
                        "source_dataset": "predictive",
                        "model_strategy": MODEL_STRATEGY_NAME,
                        "turkey_bonus_valid": "TRUE",
                        "turkey_bonus_note": f"Forecasted from {row_latest_source_year} limited-entry turkey bonus ladder with Utah split rule.",
                        "weapon": weapon,
                        "draw_system_type": TURKEY_DRAW_SYSTEM_TYPE,
                        "data_quality_flags": "|".join(flags),
                    }
                )

    modeled_rows = [row for row in rows if _clean_lower(row.get("turkey_bonus_valid")) == "true"]
    pending_rows = [row for row in rows if _clean_lower(row.get("turkey_bonus_valid")) != "true"]
    report = {
        "forecast_year": forecast_year,
        "source_years": history_years,
        "total_turkey_rows_reviewed": reviewed_turkey_rows,
        "bonus_turkey_row_count": len(rows),
        "bonus_turkey_modeled_row_count": len(modeled_rows),
        "bonus_turkey_pending_row_count": len(pending_rows),
        "excluded_general_season_turkey_row_count": excluded_general_season_rows,
        "excluded_remaining_permit_turkey_row_count": excluded_remaining_rows,
        "excluded_non_public_turkey_row_count": excluded_non_public_rows,
        "excluded_other_non_draw_turkey_row_count": excluded_other_rows,
        "modeled_turkey_hunt_code_count": len({str(row.get("hunt_code", "")).strip() for row in modeled_rows if str(row.get("hunt_code", "")).strip()}),
        "p_bonus_pool_non_null_count": sum(1 for row in rows if _clean(row.get("p_bonus_pool"))),
        "p_random_pool_non_null_count": sum(1 for row in rows if _clean(row.get("p_random_pool"))),
        "p_draw_non_null_count": sum(1 for row in rows if _clean(row.get("p_draw"))),
        "p_draw_pct_non_null_count": sum(1 for row in rows if _clean(row.get("p_draw_pct"))),
        "p_preference_draw_non_null_count": sum(1 for row in rows if _clean(row.get("p_preference_draw"))),
        "p_draw_outside_0_1_count": sum(1 for row in rows if _clean(row.get("p_draw")) and not (0.0 <= float(_clean(row.get("p_draw"))) <= 1.0)),
        "p_draw_pct_outside_0_100_count": sum(1 for row in rows if _clean(row.get("p_draw_pct")) and not (0.0 <= float(_clean(row.get("p_draw_pct"))) <= 100.0)),
        "duplicate_key_count": len([(row.get("hunt_code"), row.get("residency"), row.get("points")) for row in rows]) - len({(row.get("hunt_code"), row.get("residency"), row.get("points")) for row in rows}),
        "source_years_used_non_null_count": sum(1 for row in rows if _clean(row.get("source_years_used"))),
        "data_quality_flags_summary": dict(data_quality_counter),
    }
    return rows, report
