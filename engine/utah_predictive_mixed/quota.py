from __future__ import annotations

import math

from engine.utah_predictive_mixed.prior_year import clamp, to_float


def quota_for_row(row: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    reasons = ["OFFICIAL_2026_QUOTA_USED"]
    residency = row.get("residency", "")
    if residency == "Resident":
        quota = to_float(row.get("permit_allotment_2026_res")) or to_float(row.get("quota_2026_total"))
    elif residency == "Nonresident":
        quota = to_float(row.get("permit_allotment_2026_nr")) or to_float(row.get("quota_2026_total"))
    else:
        quota = to_float(row.get("permit_allotment_2026_total")) or to_float(row.get("quota_2026_total"))
    total = to_float(row.get("quota_2026_total")) or quota or to_float(row.get("permit_allotment_2026_total"))
    max_pool = to_float(row.get("quota_2026_max_pool"))
    random_pool = to_float(row.get("quota_2026_random_pool"))
    if quota is not None and max_pool is None:
        max_pool = math.ceil(quota * 0.50)
        random_pool = quota - max_pool
    if quota is None and total is not None and not row.get("permit_allotment_2026_res") and not row.get("permit_allotment_2026_nr"):
        reasons.append("TOTAL_ONLY_QUOTA")
    return {
        "quota_2026_total": "" if total is None else str(int(total)),
        "quota_2026_max_pool": "" if max_pool is None else str(int(max_pool)),
        "quota_2026_random_pool": "" if random_pool is None else str(int(random_pool)),
        "quota_source_status": row.get("quota_source_status") or "official",
        "quota_source_year": row.get("quota_source_year") or "2026",
        "quota_source_file": row.get("quota_source_file") or row.get("permit_allotment_2026_source_file", ""),
    }, reasons


def quota_adjusted_probability(
    p_prior: float | None, prior_public_permits: object, current_public_quota: object
) -> tuple[float | None, float, list[str]]:
    reasons: list[str] = []
    prior = to_float(prior_public_permits)
    current = to_float(current_public_quota)
    if prior in (None, 0) or current is None:
        ratio = 1.0
        reasons.append("QUOTA_RATIO_DEFAULTED")
    else:
        ratio = current / prior
    capped = min(2.0, max(0.25, ratio))
    if capped != ratio and ratio < 0.25:
        reasons.append("QUOTA_RATIO_CAPPED_LOW")
    if capped != ratio and ratio > 2.0:
        reasons.append("QUOTA_RATIO_CAPPED_HIGH")
    if ratio > 1.001:
        reasons.append("QUOTA_INCREASE")
    elif ratio < 0.999:
        reasons.append("QUOTA_DECREASE")
    else:
        reasons.append("QUOTA_UNCHANGED")
    if p_prior is None:
        return None, capped, reasons
    return clamp(p_prior * capped), capped, reasons
