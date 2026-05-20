"""Utah draw predictive umbrella strategy registry."""

from __future__ import annotations

from dataclasses import dataclass


ALGORITHM_STATUS_MODELED_BONUS = "MODELED_BONUS"
ALGORITHM_STATUS_MODELED_PREFERENCE = "MODELED_PREFERENCE"
ALGORITHM_STATUS_MODELED_ALLOCATION = "MODELED_ALLOCATION"
ALGORITHM_STATUS_MODELED_RANDOM_ONLY = "MODELED_RANDOM_ONLY"
ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING = "IN_SCOPE_MODEL_PENDING"
ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW = "EXCLUDED_NOT_PREDICTIVE_DRAW"
ALGORITHM_STATUS_OUT_OF_SCOPE_NON_TARGET = "OUT_OF_SCOPE_NON_TARGET"
ALGORITHM_STATUS_UNKNOWN_TARGET_NEEDS_REVIEW = "UNKNOWN_TARGET_NEEDS_REVIEW"

TARGET_SCOPE_TARGET = "TARGET"
TARGET_SCOPE_OUT_OF_SCOPE = "OUT_OF_SCOPE"


@dataclass(frozen=True)
class StrategySpec:
    draw_system_type: str
    module_name: str
    algorithm_status: str
    target_scope: str
    reason: str
    modeled_by_engine: bool = False
    legacy_logic_present: bool = False
    notes: str = ""
