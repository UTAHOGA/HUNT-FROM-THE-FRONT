"""Rule constants and helpers for Utah bonus predictive engine."""

from __future__ import annotations

BONUS_HUNT_TYPES = {"OIL", "LE", "PLE"}
MODEL_VERSION = "hybrid_ml_v2.1.0"
RULE_VERSION = "utah_bonus_rules_v1.1.0"


def normalize_hunt_type(hunt_type: str) -> str:
    value = (hunt_type or "").strip().upper()
    if value in {"LIMITED ENTRY", "LE"}:
        return "LE"
    if value in {"PREMIUM LIMITED ENTRY", "PLE"}:
        return "PLE"
    if value in {"ONCE IN A LIFETIME", "ONCE-IN-A-LIFETIME", "OIL", "O.I.L."}:
        return "OIL"
    return value


def is_bonus_hunt_type(hunt_type: str) -> bool:
    return normalize_hunt_type(hunt_type) in BONUS_HUNT_TYPES

