"""Phase 8 bear bonus predictive helpers for proven Utah public bear draw rows."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from typing import Iterable, Mapping

from engine.utah_bonus_predictive.monte_carlo import combine_probabilities, compute_bonus_pool_probability
from engine.utah_bonus_predictive.rules import MODEL_VERSION
from engine.utah_bonus_predictive.split import split_utah_bonus_permits

from . import (
    ALGORITHM_STATUS_MODELED_BONUS,
    StrategySpec,
    TARGET_SCOPE_TARGET,
)


MODEL_STRATEGY_NAME = "bear_bonus_phase8"
BONUS_RULE_VERSION = "utah_bear_bonus_v1.0.0"
BEAR_DRAW_SYSTEM_TYPE = "BEAR_DRAW"

LIMITED_ENTRY_BEAR_HUNT = "LIMITED_ENTRY_BEAR_HUNT"
RESTRICTED_BEAR_PURSUIT = "RESTRICTED_BEAR_PURSUIT"
STATEWIDE_BEAR_PERMIT = "STATEWIDE_BEAR_PERMIT"
HARVEST_OBJECTIVE_AVAILABILITY = "HARVEST_OBJECTIVE_AVAILABILITY"
REMAINING_PERMIT_AVAILABILITY = "REMAINING_PERMIT_AVAILABILITY"
UNLIMITED_PURSUIT_PERMIT = "UNLIMITED_PURSUIT_PERMIT"
CONSERVATION_OR_NON_PUBLIC = "CONSERVATION_OR_NON_PUBLIC"
UNKNOWN_BEAR_SUBTYPE = "UNKNOWN_BEAR_SUBTYPE"

MODELED_BEAR_SUBTYPES = {LIMITED_ENTRY_BEAR_HUNT, RESTRICTED_BEAR_PURSUIT, STATEWIDE_BEAR_PERMIT}
EXCLUDED_BEAR_SUBTYPES = {
    HARVEST_OBJECTIVE_AVAILABILITY,
    REMAINING_PERMIT_AVAILABILITY,
    UNLIMITED_PURSUIT_PERMIT,
    CONSERVATION_OR_NON_PUBLIC,
}

STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type=BEAR_DRAW_SYSTEM_TYPE,
        module_name="engine.utah_draw_predictive.bear",
        algorithm_status=ALGORITHM_STATUS_MODELED_BONUS,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Public limited-entry and restricted-pursuit bear rows use the Utah bonus model only when the source history proves real draw status, valid quota, and modeled bonus probabilities.",
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
        for key in ("hunt_code", "hunt_name", "species", "sex_type", "hunt_type", "hunt_class", "weapon", "draw_pool", "source_file")
    )


def _species_is_black_bear(row: Mapping[str, object]) -> bool:
    species = _clean_lower(row.get("species"))
    return species in {"black bear", "bear"} or "black bear" in species


def _hunt_code_is_bear(row: Mapping[str, object]) -> bool:
    return _clean(row.get("hunt_code")).upper().startswith("BR")


def is_bear_row(row: Mapping[str, object]) -> bool:
    if _species_is_black_bear(row):
        return True
    text = _joined_text(row)
    if _hunt_code_is_bear(row) and "bear" in text and "bighorn" not in text:
        return True
    return False


def classify_bear_subtype(row: Mapping[str, object]) -> str:
    if not is_bear_row(row):
        return UNKNOWN_BEAR_SUBTYPE
    text = _joined_text(row)
    hunt_type = _clean_lower(row.get("hunt_type"))
    hunt_class = _clean_lower(row.get("hunt_class"))
    weapon = _clean_lower(row.get("weapon"))
    draw_pool = _clean_lower(row.get("draw_pool"))
    hunt_code = _clean(row.get("hunt_code")).upper()

    if hunt_code == "BR1000" or "statewide permit" in text:
        return STATEWIDE_BEAR_PERMIT
    if hunt_code in {"BR1007", "BR1018"}:
        return UNLIMITED_PURSUIT_PERMIT
    if (
        "cwmu" in text
        or any(token in text for token in ("conservation", "expo", "sportsman", "statewide permit", "private land", "landowner", "private"))
        or hunt_class == "private"
        or draw_pool == "sportsman"
    ):
        return CONSERVATION_OR_NON_PUBLIC
    if "remaining permit" in text or " otc" in f" {text}" or "over the counter" in text:
        return REMAINING_PERMIT_AVAILABILITY
    if "harvest objective" in text:
        return HARVEST_OBJECTIVE_AVAILABILITY
    if "restricted pursuit" in text or hunt_type == "pursuit" or hunt_type.startswith("pursuit") or weapon == "pursuit only":
        return RESTRICTED_BEAR_PURSUIT
    if "spot and stalk" in text:
        return LIMITED_ENTRY_BEAR_HUNT
    if "limited entry" in text or "limited-entry" in text:
        return LIMITED_ENTRY_BEAR_HUNT
    return UNKNOWN_BEAR_SUBTYPE


def is_supported_bear_bonus_row(row: Mapping[str, object]) -> bool:
    return classify_bear_subtype(row) in MODELED_BEAR_SUBTYPES


def is_remaining_bear_row(row: Mapping[str, object]) -> bool:
    return classify_bear_subtype(row) == REMAINING_PERMIT_AVAILABILITY


def is_nonpublic_bear_row(row: Mapping[str, object]) -> bool:
    return classify_bear_subtype(row) == CONSERVATION_OR_NON_PUBLIC


def is_harvest_objective_bear_row(row: Mapping[str, object]) -> bool:
    return classify_bear_subtype(row) == HARVEST_OBJECTIVE_AVAILABILITY


def is_excluded_bear_row(row: Mapping[str, object]) -> bool:
    subtype = classify_bear_subtype(row)
    if subtype == STATEWIDE_BEAR_PERMIT:
        text = _joined_text(row)
        hunt_code = _clean(row.get("hunt_code")).upper()
        return hunt_code == "BR1000" or "sportsman" in text or "no_draw_odds" in text
    return subtype in EXCLUDED_BEAR_SUBTYPES


def is_modeled_bear_row(row: Mapping[str, object]) -> bool:
    return (
        _clean_lower(row.get("model_strategy")) == MODEL_STRATEGY_NAME
        and _clean_lower(row.get("bear_bonus_valid")) in {"1", "true", "yes", "y"}
        and _clean(row.get("draw_system_type")) == BEAR_DRAW_SYSTEM_TYPE
    )


def _is_proven_bonus_bear_truth_row(row: Mapping[str, object]) -> bool:
    if not is_bear_row(row):
        return False
    if classify_bear_subtype(row) not in MODELED_BEAR_SUBTYPES:
        return False
    if _clean_lower(row.get("draw_pool")) not in {"", "standard"}:
        return False
    source_file = _clean_lower(row.get("source_file"))
    if source_file in {"database.csv", "sportsman_permit_no_draw_odds"}:
        return False
    return True


def _build_truth_ladders(
    truth_rows: Iterable[Mapping[str, object]],
    history_years: set[int],
) -> tuple[
    dict[tuple[str, int, str, str], dict[int, dict[str, int]]],
    dict[str, dict[str, str]],
    dict[tuple[str, int], dict[str, int]],
]:
    ladders: dict[tuple[str, int, str, str], dict[int, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"eligible": 0, "bonus": 0, "regular": 0, "total": 0})
    )
    meta: dict[str, dict[str, str]] = {}
    total_drawn_by_code_year: dict[tuple[str, int], dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in truth_rows:
        year = _to_int(row.get("year"))
        if year not in history_years or not _is_proven_bonus_bear_truth_row(row):
            continue
        subtype = classify_bear_subtype(row)
        hunt_code = _clean(row.get("hunt_code")).upper()
        residency = _clean(row.get("residency")) or "Resident"
        points = _to_int(row.get("points"))
        if not hunt_code:
            continue

        eligible = _to_int(row.get("eligible_applicants"))
        bonus = _to_int(row.get("bonus_permits"))
        regular = _to_int(row.get("regular_permits"))
        total = _to_int(row.get("total_permits"))
        ladders[(subtype, year, hunt_code, residency)][points]["eligible"] += eligible
        ladders[(subtype, year, hunt_code, residency)][points]["bonus"] += bonus
        ladders[(subtype, year, hunt_code, residency)][points]["regular"] += regular
        ladders[(subtype, year, hunt_code, residency)][points]["total"] += total
        total_drawn_by_code_year[(hunt_code, year)][residency] += total

        if hunt_code not in meta:
            meta[hunt_code] = {
                "hunt_name": _clean(row.get("hunt_name")),
                "species": _clean(row.get("species")),
                "hunt_type": _clean(row.get("hunt_type")),
                "hunt_class": _clean(row.get("hunt_class")),
                "weapon": _clean(row.get("weapon")),
                "sex_type": _clean(row.get("sex_type")),
                "source_file": _clean(row.get("source_file")),
            }

    return ladders, meta, total_drawn_by_code_year


def _build_retention_and_zero_growth(
    ladders: Mapping[tuple[str, int, str, str], dict[int, dict[str, int]]],
) -> tuple[dict[str, float], float]:
    retention_samples: dict[str, list[float]] = defaultdict(list)
    zero_growth_samples: list[float] = []
    years_by_subtype_code_res: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for subtype, year, hunt_code, residency in ladders:
        years_by_subtype_code_res[(subtype, hunt_code, residency)].append(year)

    for (subtype, hunt_code, residency), years in years_by_subtype_code_res.items():
        for prior_year in sorted(years):
            next_year = prior_year + 1
            if next_year not in years:
                continue
            prior = ladders[(subtype, prior_year, hunt_code, residency)]
            nxt = ladders[(subtype, next_year, hunt_code, residency)]
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
        "1": 0.83,
        "2_3": 0.87,
        "4_5": 0.91,
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
        retained = unsuccessful_prior * retention_by_band.get(_band_for_points(points - 1), 0.85)
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


def _draw_outlook(probability: float, pending: bool = False, excluded: bool = False, availability: bool = False) -> str:
    if availability:
        return "REMAINING PERMIT / AVAILABILITY"
    if excluded:
        return "NOT A DRAW"
    if pending:
        return "MODEL PENDING"
    if probability >= 0.75:
        return "GREEN LIGHT"
    if probability > 0.10:
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
    db_row: Mapping[str, object],
    hunt_code: str,
    residency: str,
    latest_year: int,
    total_drawn_by_code_year: Mapping[tuple[str, int], dict[str, int]],
) -> int:
    res_specific = _to_int(db_row.get("permits_2026_res"))
    nr_specific = _to_int(db_row.get("permits_2026_nr"))
    total = _to_int(db_row.get("permits_2026_total"))
    if res_specific or nr_specific:
        return res_specific if residency == "Resident" else nr_specific
    observed = total_drawn_by_code_year.get((hunt_code, latest_year), {})
    observed_total = sum(int(value) for value in observed.values())
    if total <= 0:
        return 0
    if observed_total <= 0:
        return total if residency == "Resident" else 0
    resident_drawn = int(observed.get("Resident", 0))
    resident_quota = max(0, min(total, round(total * (resident_drawn / max(observed_total, 1)))))
    return resident_quota if residency == "Resident" else max(0, total - resident_quota)


def _data_quality_flags(
    available_years: list[int],
    total_applicants: int,
    public_quota: int,
    max_point_permits: int,
    subtype: str,
) -> list[str]:
    flags: list[str] = ["FIRST_CHOICE_ONLY_MODEL"]
    if len(available_years) == 1:
        flags.append("MISSING_MULTIPLE_YEARS")
    if total_applicants < 5:
        flags.append("LOW_APPLICANT_COUNT")
    if public_quota == 1:
        flags.append("ONE_PERMIT_RANDOM_ONLY")
    if max_point_permits == 0 and public_quota > 0:
        flags.append("NO_MAX_POINT_POOL")
    if subtype == RESTRICTED_BEAR_PURSUIT:
        flags.append("RESTRICTED_PURSUIT_MODELED")
    return flags


def _permit_availability_type(subtype: str) -> str:
    if subtype == STATEWIDE_BEAR_PERMIT:
        return "STATEWIDE_PERMIT"
    if subtype == HARVEST_OBJECTIVE_AVAILABILITY:
        return "HARVEST_OBJECTIVE"
    if subtype == UNLIMITED_PURSUIT_PERMIT:
        return "UNLIMITED_PURSUIT"
    if subtype == REMAINING_PERMIT_AVAILABILITY:
        return "REMAINING_PERMIT"
    if subtype == CONSERVATION_OR_NON_PUBLIC:
        return "NON_PUBLIC_EXCLUDED"
    if subtype in MODELED_BEAR_SUBTYPES:
        return "DRAW_ODDS"
    return "UNKNOWN"


def _base_row(
    *,
    forecast_year: int,
    source_years_used_text: str,
    source_year_count: int,
    earliest_source_year: int,
    latest_source_year: int,
    hunt_code: str,
    hunt_name: str,
    species: str,
    sex_type: str,
    hunt_type: str,
    hunt_class: str,
    residency: str,
    public_permits_2025: int,
    public_permits_2026: int,
    weapon: str,
    subtype: str,
) -> dict[str, object]:
    return {
        "model_version": MODEL_VERSION,
        "rule_version": BONUS_RULE_VERSION,
        "year": str(forecast_year),
        "forecast_year": str(forecast_year),
        "hunt_code": hunt_code,
        "hunt_name": hunt_name,
        "species": species,
        "sex_type": sex_type,
        "hunt_type": hunt_type,
        "hunt_class": hunt_class,
        "residency": residency,
        "draw_pool": "standard",
        "public_permits_2025": public_permits_2025,
        "public_permits_2026": public_permits_2026,
        "source_years_used": source_years_used_text,
        "source_year_count": source_year_count,
        "latest_source_year": latest_source_year,
        "earliest_source_year": earliest_source_year,
        "source_dataset": "predictive",
        "model_strategy": MODEL_STRATEGY_NAME,
        "weapon": weapon,
        "draw_system_type": BEAR_DRAW_SYSTEM_TYPE,
        "bear_draw_subtype": subtype,
        "permit_availability_type": _permit_availability_type(subtype),
        "harvest_objective_unit_count": "",
        "harvest_objective_take_quota": "",
        "harvest_objective_remaining_quota": "",
        "harvest_objective_status": "",
        "p_availability": "",
        "availability_pct": "",
        "closure_risk": "",
        "sellout_or_closure_risk": "",
    }


def build_bear_bonus_predictions(
    truth_rows: Iterable[Mapping[str, object]],
    db_rows: Iterable[Mapping[str, object]],
    forecast_year: int,
    history_years: list[int],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    history_year_set = {int(year) for year in history_years}
    source_years_used_text = ",".join(str(year) for year in history_years)
    source_year_count = len(history_years)
    default_earliest_source_year = min(history_years)
    default_latest_source_year = max(history_years)
    ladders, meta, total_drawn_by_code_year = _build_truth_ladders(truth_rows, history_year_set)
    retention_by_band, zero_growth = _build_retention_and_zero_growth(ladders)

    years_by_subtype_code_res: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for subtype, year, hunt_code, residency in ladders:
        years_by_subtype_code_res[(subtype, hunt_code, residency)].append(year)

    rows: list[dict[str, object]] = []
    report_counts = Counter()
    data_quality_counter: Counter[str] = Counter()
    review_rows: list[dict[str, object]] = []

    for db_row in db_rows:
        if not is_bear_row(db_row):
            continue
        if _clean(db_row.get("hunt_code")).upper() == "BR1000" or "sportsman" in _joined_text(db_row):
            continue
        review_rows.append(dict(db_row))

        hunt_code = _clean(db_row.get("hunt_code")).upper()
        if not hunt_code:
            continue
        subtype = classify_bear_subtype(db_row)
        hunt_name = _clean(db_row.get("hunt_name")) or meta.get(hunt_code, {}).get("hunt_name", "")
        species = _clean(db_row.get("species")) or meta.get(hunt_code, {}).get("species", "Black Bear")
        sex_type = _clean(db_row.get("sex_type")) or meta.get(hunt_code, {}).get("sex_type", "")
        hunt_type = _clean(db_row.get("hunt_type")) or meta.get(hunt_code, {}).get("hunt_type", "")
        weapon = _clean(db_row.get("weapon")) or meta.get(hunt_code, {}).get("weapon", "")
        hunt_class = "Public"
        if subtype == CONSERVATION_OR_NON_PUBLIC:
            hunt_class = _clean(db_row.get("hunt_class")) or "Non-Public / Excluded"

        for residency in ("Resident", "Nonresident"):
            available_years = sorted(set(years_by_subtype_code_res.get((subtype, hunt_code, residency), [])))
            latest_year = available_years[-1] if available_years else default_latest_source_year
            earliest_source_year = available_years[0] if available_years else default_earliest_source_year
            latest_ladder = ladders.get((subtype, latest_year, hunt_code, residency), {}) if available_years else {}
            prior_total = sum(int(values.get("total", 0)) for values in latest_ladder.values())
            public_quota = _forecast_quota_for_residency(db_row, hunt_code, residency, latest_year, total_drawn_by_code_year)
            base = _base_row(
                forecast_year=forecast_year,
                source_years_used_text=source_years_used_text,
                source_year_count=source_year_count,
                earliest_source_year=earliest_source_year,
                latest_source_year=latest_year,
                hunt_code=hunt_code,
                hunt_name=hunt_name,
                species=species,
                sex_type=sex_type,
                hunt_type=hunt_type,
                hunt_class=hunt_class,
                residency=residency,
                public_permits_2025=prior_total,
                public_permits_2026=public_quota,
                weapon=weapon,
                subtype=subtype,
            )

            if subtype == UNLIMITED_PURSUIT_PERMIT:
                row = dict(base)
                row.update(
                    {
                        "points": "",
                        "p_preference_draw": "",
                        "p_bonus_pool": "",
                        "p_random_pool": "",
                        "p_draw": "",
                        "p_bonus_pool_pct": "",
                        "p_random_pool_pct": "",
                        "p_draw_pct": "",
                        "draw_outlook": _draw_outlook(0.0, excluded=True, availability=True),
                        "bear_bonus_valid": "FALSE",
                        "bear_bonus_note": "Unlimited pursuit availability is not a draw-odds row.",
                        "data_quality_flags": "",
                        "p_availability": "1.000000",
                        "availability_pct": "100.000",
                        "sellout_or_closure_risk": "NONE",
                    }
                )
                rows.append(row)
                report_counts["excluded"] += 1
                continue

            if subtype in EXCLUDED_BEAR_SUBTYPES or (subtype == STATEWIDE_BEAR_PERMIT and is_excluded_bear_row(base)):
                row = dict(base)
                row.update(
                    {
                        "points": "",
                        "p_preference_draw": "",
                        "p_bonus_pool": "",
                        "p_random_pool": "",
                        "p_draw": "",
                        "p_bonus_pool_pct": "",
                        "p_random_pool_pct": "",
                        "p_draw_pct": "",
                        "draw_outlook": _draw_outlook(0.0, excluded=True, availability=subtype in {HARVEST_OBJECTIVE_AVAILABILITY, REMAINING_PERMIT_AVAILABILITY}),
                        "bear_bonus_valid": "FALSE",
                        "bear_bonus_note": "Bear row is in scope, but this subtype is not a predictive public draw-probability target.",
                        "data_quality_flags": "",
                    }
                )
                rows.append(row)
                report_counts["excluded"] += 1
                continue

            if subtype not in MODELED_BEAR_SUBTYPES:
                row = dict(base)
                row.update(
                    {
                        "points": "",
                        "p_preference_draw": "",
                        "p_bonus_pool": "",
                        "p_random_pool": "",
                        "p_draw": "",
                        "p_bonus_pool_pct": "",
                        "p_random_pool_pct": "",
                        "p_draw_pct": "",
                        "draw_outlook": _draw_outlook(0.0, pending=True),
                        "bear_bonus_valid": "FALSE",
                        "bear_bonus_note": "Bear subtype could not be cleanly proven from public draw source data.",
                        "data_quality_flags": "BEAR_SUBTYPE_AMBIGUOUS",
                    }
                )
                data_quality_counter["BEAR_SUBTYPE_AMBIGUOUS"] += 1
                rows.append(row)
                report_counts["pending"] += 1
                continue

            if not available_years or public_quota <= 0:
                flags = []
                if not available_years:
                    flags.append("MISSING_PROVEN_BEAR_DRAW_HISTORY")
                if public_quota <= 0:
                    flags.append("MISSING_FORECAST_QUOTA")
                flags.append("FIRST_CHOICE_ONLY_MODEL")
                for flag in flags:
                    data_quality_counter[flag] += 1
                row = dict(base)
                row.update(
                    {
                        "points": "",
                        "p_preference_draw": "",
                        "p_bonus_pool": "",
                        "p_random_pool": "",
                        "p_draw": "",
                        "p_bonus_pool_pct": "",
                        "p_random_pool_pct": "",
                        "p_draw_pct": "",
                        "draw_outlook": _draw_outlook(0.0, pending=True),
                        "bear_bonus_valid": "FALSE",
                        "bear_bonus_note": "Missing proven bear history or usable 2026 public quota for this residency.",
                        "data_quality_flags": "|".join(flags),
                    }
                )
                rows.append(row)
                report_counts["pending"] += 1
                continue

            split = split_utah_bonus_permits(public_quota)
            max_point_permits = split.maxPointPermits
            random_permits = split.randomPermits
            forecast_ladder = _forecast_applicant_ladder(latest_ladder, retention_by_band, zero_growth)
            if not forecast_ladder:
                flags = ["LOW_APPLICANT_COUNT", "FIRST_CHOICE_ONLY_MODEL"]
                for flag in flags:
                    data_quality_counter[flag] += 1
                row = dict(base)
                row.update(
                    {
                        "points": "",
                        "p_preference_draw": "",
                        "p_bonus_pool": "",
                        "p_random_pool": "",
                        "p_draw": "",
                        "p_bonus_pool_pct": "",
                        "p_random_pool_pct": "",
                        "p_draw_pct": "",
                        "draw_outlook": _draw_outlook(0.0, pending=True),
                        "bear_bonus_valid": "FALSE",
                        "bear_bonus_note": "Proven bear history existed, but the forecast ladder was empty.",
                        "data_quality_flags": "|".join(flags),
                    }
                )
                rows.append(row)
                report_counts["pending"] += 1
                continue

            prior_guaranteed = _guaranteed_level({points: int(values.get("eligible", 0)) for points, values in latest_ladder.items()}, prior_total)
            forecast_guaranteed = _guaranteed_level(forecast_ladder, public_quota)
            total_applicants = sum(forecast_ladder.values())
            flags = _data_quality_flags(available_years, total_applicants, public_quota, max_point_permits, subtype)
            for flag in flags:
                data_quality_counter[flag] += 1

            for points in sorted(forecast_ladder.keys(), reverse=True):
                applicants_by_points = {int(level): int(count) for level, count in forecast_ladder.items()}
                p_bonus_pool, applicants_above, applicants_at_level = compute_bonus_pool_probability(points, applicants_by_points, max_point_permits)
                p_random_pool = _weighted_random_probability(points, applicants_by_points, random_permits)
                p_draw = combine_probabilities(p_bonus_pool, p_random_pool)
                row = dict(base)
                row.update(
                    {
                        "points": str(points),
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
                        "gap": "" if forecast_guaranteed is None else str(forecast_guaranteed - points),
                        "delta_gap": "" if forecast_guaranteed is None or prior_guaranteed is None else str((forecast_guaranteed - points) - (prior_guaranteed - points)),
                        "status": _status(max_point_permits, random_permits, p_bonus_pool),
                        "trend": _trend(prior_guaranteed, forecast_guaranteed),
                        "draw_outlook": _draw_outlook(p_draw),
                        "bear_bonus_valid": "TRUE",
                        "bear_bonus_note": f"Forecasted from {latest_year} public bear draw history with Utah bonus split rules.",
                        "data_quality_flags": "|".join(flags),
                    }
                )
                rows.append(row)
                report_counts["modeled"] += 1

    observed_history_rows = [row for row in truth_rows if is_bear_row(row)]
    review_counter = Counter(classify_bear_subtype(row) for row in review_rows)
    modeled_rows = [row for row in rows if _clean(row.get("bear_bonus_valid")) == "TRUE"]

    report = {
        "forecast_year": forecast_year,
        "source_years": history_years,
        "total_bear_rows_reviewed": len(review_rows),
        "bear_rows_seen_observed_history": len(observed_history_rows),
        "bear_rows_seen_active_predictive": len(rows),
        "bear_rows_by_bear_draw_subtype": dict(sorted(review_counter.items())),
        "bear_rows_by_algorithm_status": {
            "MODELED_BONUS": report_counts["modeled"],
            "IN_SCOPE_MODEL_PENDING": report_counts["pending"],
            "EXCLUDED_NOT_PREDICTIVE_DRAW": report_counts["excluded"],
        },
        "bear_draw_active_predictive_row_count": len(rows),
        "bear_draw_modeled_row_count": report_counts["modeled"],
        "bear_draw_pending_row_count": report_counts["pending"],
        "bear_draw_excluded_non_draw_row_count": report_counts["excluded"],
        "modeled_bear_hunt_code_count": len({str(row.get("hunt_code", "")).strip() for row in modeled_rows if str(row.get("hunt_code", "")).strip()}),
        "limited_entry_bear_modeled_row_count": sum(1 for row in modeled_rows if row.get("bear_draw_subtype") == LIMITED_ENTRY_BEAR_HUNT),
        "restricted_pursuit_modeled_row_count": sum(1 for row in modeled_rows if row.get("bear_draw_subtype") == RESTRICTED_BEAR_PURSUIT),
        "harvest_objective_excluded_or_availability_pending_row_count": sum(1 for row in rows if row.get("bear_draw_subtype") == HARVEST_OBJECTIVE_AVAILABILITY),
        "remaining_permit_excluded_or_availability_pending_row_count": sum(1 for row in rows if row.get("bear_draw_subtype") == REMAINING_PERMIT_AVAILABILITY),
        "statewide_bear_permit_row_count": sum(1 for row in rows if row.get("bear_draw_subtype") == STATEWIDE_BEAR_PERMIT),
        "statewide_bear_permit_modeled_row_count": sum(1 for row in rows if row.get("bear_draw_subtype") == STATEWIDE_BEAR_PERMIT and row.get("algorithm_status") == "MODELED_BONUS"),
        "statewide_bear_permit_pending_row_count": sum(1 for row in rows if row.get("bear_draw_subtype") == STATEWIDE_BEAR_PERMIT and row.get("algorithm_status") == "IN_SCOPE_MODEL_PENDING"),
        "statewide_bear_permit_excluded_row_count": sum(1 for row in rows if row.get("bear_draw_subtype") == STATEWIDE_BEAR_PERMIT and row.get("algorithm_status") == "EXCLUDED_NOT_PREDICTIVE_DRAW"),
        "statewide_bear_permit_p_draw_non_null_count": sum(1 for row in rows if row.get("bear_draw_subtype") == STATEWIDE_BEAR_PERMIT and _clean(row.get("p_draw"))),
        "harvest_objective_row_count": sum(1 for row in rows if row.get("bear_draw_subtype") == HARVEST_OBJECTIVE_AVAILABILITY),
        "harvest_objective_p_draw_non_null_count": sum(1 for row in rows if row.get("bear_draw_subtype") == HARVEST_OBJECTIVE_AVAILABILITY and _clean(row.get("p_draw"))),
        "harvest_objective_availability_fields_populated_count": sum(
            1
            for row in rows
            if row.get("bear_draw_subtype") == HARVEST_OBJECTIVE_AVAILABILITY
            and any(_clean(row.get(field)) for field in ("p_availability", "availability_pct", "harvest_objective_take_quota", "harvest_objective_status"))
        ),
        "unlimited_pursuit_permit_row_count": sum(1 for row in rows if row.get("bear_draw_subtype") == UNLIMITED_PURSUIT_PERMIT),
        "unlimited_pursuit_permit_p_draw_non_null_count": sum(1 for row in rows if row.get("bear_draw_subtype") == UNLIMITED_PURSUIT_PERMIT and _clean(row.get("p_draw"))),
        "conservation_or_non_public_row_count": sum(1 for row in rows if row.get("bear_draw_subtype") == CONSERVATION_OR_NON_PUBLIC),
        "conservation_or_non_public_p_draw_non_null_count": sum(1 for row in rows if row.get("bear_draw_subtype") == CONSERVATION_OR_NON_PUBLIC and _clean(row.get("p_draw"))),
        "non_public_excluded_bear_row_count": sum(1 for row in rows if row.get("bear_draw_subtype") == CONSERVATION_OR_NON_PUBLIC),
        "p_bonus_pool_non_null_count": sum(1 for row in rows if _clean(row.get("p_bonus_pool"))),
        "p_random_pool_non_null_count": sum(1 for row in rows if _clean(row.get("p_random_pool"))),
        "p_draw_non_null_count": sum(1 for row in rows if _clean(row.get("p_draw"))),
        "p_draw_pct_non_null_count": sum(1 for row in rows if _clean(row.get("p_draw_pct"))),
        "p_preference_draw_non_null_count": sum(1 for row in rows if _clean(row.get("p_preference_draw"))),
        "p_draw_outside_0_1_count": sum(1 for row in rows if _clean(row.get("p_draw")) and not (0.0 <= float(str(row.get("p_draw"))) <= 1.0)),
        "p_draw_pct_outside_0_100_count": sum(1 for row in rows if _clean(row.get("p_draw_pct")) and not (0.0 <= float(str(row.get("p_draw_pct"))) <= 100.0)),
        "duplicate_key_count": len(rows) - len({(str(row.get("hunt_code", "")).strip(), str(row.get("residency", "")).strip(), str(row.get("points", "")).strip()) for row in rows}),
        "source_years_used_non_null_count": sum(1 for row in rows if _clean(row.get("source_years_used"))),
        "first_choice_only_model_count": sum(1 for row in rows if "FIRST_CHOICE_ONLY_MODEL" in _clean(row.get("data_quality_flags")).split("|")),
        "bear_subtype_ambiguous_count": sum(1 for row in rows if "BEAR_SUBTYPE_AMBIGUOUS" in _clean(row.get("data_quality_flags")).split("|")),
        "multiseason_limited_entry_bear_modeled_row_count": sum(
            1 for row in modeled_rows if "multiseason" in _clean_lower(row.get("hunt_type"))
        ),
        "spot_and_stalk_bear_modeled_row_count": sum(
            1 for row in modeled_rows if "spot and stalk" in _clean_lower(row.get("hunt_type"))
        ),
        "data_quality_flags_summary": dict(sorted(data_quality_counter.items())),
    }
    return rows, report
