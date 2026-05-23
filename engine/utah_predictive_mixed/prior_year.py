from __future__ import annotations

import re


BLANKS = {"", "-", "--", "---", "–", "—", "N/A", "NA", "None", "null"}


def to_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in BLANKS or text.lower() in {v.lower() for v in BLANKS}:
        return None
    text = text.replace(",", "").replace("%", "")
    try:
        return float(text)
    except ValueError:
        return None


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def parse_success_ratio(value: object) -> float | None:
    text = str(value or "").strip()
    if not text or text.upper() == "N/A":
        return None
    match = re.search(r"1\s+in\s+([0-9.]+)", text, re.I)
    if match:
        denominator = to_float(match.group(1))
        if denominator and denominator > 0:
            return clamp(1.0 / denominator)
    pct = to_float(text)
    if pct is not None:
        return clamp(pct / 100.0 if pct > 1 else pct)
    return None


def prior_year_baseline(row: dict[str, str]) -> tuple[float | None, dict[str, str], list[str]]:
    reasons: list[str] = []
    applicants = to_float(row.get("applicants") or row.get("eligible_applicants") or row.get("applicants_at_level"))
    bonus = to_float(row.get("bonus_permits")) or 0.0
    regular = to_float(row.get("regular_permits")) or 0.0
    total = to_float(row.get("total_permits"))
    success_count = total if total is not None else bonus + regular
    success_rate = parse_success_ratio(row.get("success_ratio"))
    if success_rate is None and applicants and applicants > 0:
        success_rate = clamp((success_count or 0.0) / applicants)
    if applicants in (None, 0):
        reasons.append("PRIOR_YEAR_NO_APPLICANTS")
        return None, {
            "prior_year_applicants": "" if applicants is None else str(int(applicants)),
            "prior_year_total_permits": "" if total is None else str(int(total)),
            "prior_year_bonus_permits": str(int(bonus)),
            "prior_year_regular_permits": str(int(regular)),
            "prior_year_success_count": "" if success_count is None else str(int(success_count)),
            "prior_year_success_rate": "",
            "prior_year_draw_odds_pct": "",
        }, reasons
    if not success_count:
        reasons.append("PRIOR_YEAR_ZERO_SUCCESS")
        success_rate = 0.0
    return clamp(success_rate or 0.0), {
        "prior_year_applicants": str(int(applicants)),
        "prior_year_total_permits": "" if total is None else str(int(total)),
        "prior_year_bonus_permits": str(int(bonus)),
        "prior_year_regular_permits": str(int(regular)),
        "prior_year_success_count": "" if success_count is None else str(int(success_count)),
        "prior_year_success_rate": f"{clamp(success_rate or 0.0):.6f}",
        "prior_year_draw_odds_pct": f"{100 * clamp(success_rate or 0.0):.3f}",
    }, reasons
