"""Transparent hunt quality scoring for Utah engine V1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from .schema import to_float, to_int


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class QualityScore:
    hunt_quality_score: float
    success_rate_score: float
    harvest_score: float
    hunters_afield_score: float
    days_score: float
    trend_score: float
    permit_stability_score: float
    age_quality_score: float
    average_age_harvested: Optional[float]
    age_data_available: bool
    age_quality_source_field: str


AGE_FIELD_CANDIDATES = (
    "average_age_harvested",
    "avg_age_harvested",
    "average_age",
    "avg_age",
    "mean_age_harvested",
    "mean_age",
    "harvest_average_age",
    "average_age_2025",
    "avg_age_2025",
    "bull_age",
    "buck_age",
    "ram_age",
    "trophy_age",
)

SPECIES_AGE_REFERENCE = {
    "deer": 5.0,
    "elk": 6.0,
    "pronghorn": 4.5,
    "moose": 6.5,
    "bison": 7.0,
    "sheep": 8.0,
    "mountain goat": 7.5,
    "goat": 7.5,
}

TROPHY_DRAW_SYSTEMS = {
    "BONUS_OIL_BIG_GAME",
    "BONUS_LE_BIG_GAME",
    "BONUS_PLE_BIG_GAME",
    "BONUS_CWMU_BIG_GAME",
    "BONUS_ANTLERLESS_MOOSE",
    "BONUS_EWE_BIGHORN",
}


def _species_age_reference(species: str) -> float:
    species_lower = (species or "").strip().lower()
    for token, ref in SPECIES_AGE_REFERENCE.items():
        if token in species_lower:
            return ref
    return 6.0


def _is_trophy_weighted_hunt(species: str, hunt_class: str, draw_system_type: str) -> bool:
    draw_system = (draw_system_type or "").strip().upper()
    if draw_system in TROPHY_DRAW_SYSTEMS:
        return True
    text = f"{species or ''} {hunt_class or ''}".lower()
    return any(token in text for token in ("limited entry", "premium limited", "once-in-a-lifetime", "once in a lifetime", "cwmu", "o.i.l.", "oil"))


def compute_age_quality_score(
    row: Mapping[str, object],
    species: str,
    hunt_class: str,
    draw_system_type: str,
) -> tuple[float, Optional[float], bool, str]:
    age_value: Optional[float] = None
    source_field = ""
    for field in AGE_FIELD_CANDIDATES:
        parsed = to_float(row.get(field))
        if parsed is None:
            continue
        age_value = parsed
        source_field = field
        break

    if age_value is None:
        return 50.0, None, False, ""

    reference = _species_age_reference(species)
    score = max(0.0, min(100.0, (age_value / max(reference, 0.1)) * 100.0))
    return score, age_value, True, source_field


def compute_hunt_quality_score(
    harvest_row: Mapping[str, object] | None,
    trend: str,
    permit_stability_score: float,
    species: str = "",
    hunt_class: str = "",
    draw_system_type: str = "",
) -> QualityScore:
    row = harvest_row or {}

    success_rate_pct = to_float(row.get("success_percent") or row.get("percentSuccess") or row.get("harvest_success_percent_2025"))
    if success_rate_pct is None:
        success_rate_pct = to_float(row.get("avgSatisfaction"))
    if success_rate_pct is None:
        success_rate_score = 50.0
    else:
        if success_rate_pct <= 1.0:
            success_rate_pct *= 100.0
        success_rate_score = max(0.0, min(100.0, success_rate_pct))

    harvest = to_float(row.get("harvest") or row.get("success_harvest") or row.get("harvest_2025"))
    permits = to_float(row.get("permits") or row.get("public_permits_2025"))
    harvest_ratio = (harvest / permits) if (harvest is not None and permits is not None and permits > 0) else None
    harvest_score = 50.0 if harvest_ratio is None else _clamp01(harvest_ratio) * 100.0

    hunters = to_float(row.get("hunters") or row.get("success_hunters") or row.get("hunters_afield"))
    hunters_afield_score = 50.0 if hunters is None else min(100.0, max(0.0, hunters))

    mean_days = to_float(row.get("avgDays") or row.get("mean_days_hunted") or row.get("harvest_average_days_2025"))
    if mean_days is None:
        days_score = 50.0
    else:
        # Lower days hunted is better in this simple conservative score.
        days_score = max(0.0, min(100.0, 100.0 - (mean_days * 8.0)))

    trend_upper = str(trend or "").strip().upper()
    trend_score = 50.0
    if trend_upper == "GREEN":
        trend_score = 75.0
    elif trend_upper == "RED":
        trend_score = 25.0

    permit_stability_score = max(0.0, min(100.0, permit_stability_score))
    age_quality_score, avg_age_harvested, age_data_available, age_source_field = compute_age_quality_score(
        row=row,
        species=species,
        hunt_class=hunt_class,
        draw_system_type=draw_system_type,
    )

    if _is_trophy_weighted_hunt(species=species, hunt_class=hunt_class, draw_system_type=draw_system_type):
        hunt_quality_score = (
            (0.25 * success_rate_score)
            + (0.25 * age_quality_score)
            + (0.15 * harvest_score)
            + (0.10 * hunters_afield_score)
            + (0.10 * days_score)
            + (0.10 * trend_score)
            + (0.05 * permit_stability_score)
        )
    else:
        hunt_quality_score = (
            (0.30 * success_rate_score)
            + (0.20 * harvest_score)
            + (0.15 * hunters_afield_score)
            + (0.10 * days_score)
            + (0.15 * trend_score)
            + (0.10 * permit_stability_score)
        )

    return QualityScore(
        hunt_quality_score=round(hunt_quality_score, 3),
        success_rate_score=round(success_rate_score, 3),
        harvest_score=round(harvest_score, 3),
        hunters_afield_score=round(hunters_afield_score, 3),
        days_score=round(days_score, 3),
        trend_score=round(trend_score, 3),
        permit_stability_score=round(permit_stability_score, 3),
        age_quality_score=round(age_quality_score, 3),
        average_age_harvested=None if avg_age_harvested is None else round(avg_age_harvested, 3),
        age_data_available=age_data_available,
        age_quality_source_field=age_source_field,
    )


def compute_permit_stability_score(current_permits: Optional[int], prior_permits: Optional[int]) -> float:
    if current_permits is None or prior_permits is None:
        return 50.0
    if prior_permits <= 0 and current_permits <= 0:
        return 100.0
    if prior_permits <= 0:
        return 40.0
    delta_ratio = abs(current_permits - prior_permits) / max(prior_permits, 1)
    return round(max(0.0, min(100.0, 100.0 - (delta_ratio * 100.0))), 3)
