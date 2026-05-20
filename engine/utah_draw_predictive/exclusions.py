"""Explicit exclusions and out-of-scope declarations."""

from __future__ import annotations

from . import (
    ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW,
    ALGORITHM_STATUS_OUT_OF_SCOPE_NON_TARGET,
    ALGORITHM_STATUS_UNKNOWN_TARGET_NEEDS_REVIEW,
    StrategySpec,
    TARGET_SCOPE_OUT_OF_SCOPE,
    TARGET_SCOPE_TARGET,
)


STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type="LANDOWNER_BIG_GAME",
        module_name="engine.utah_draw_predictive.exclusions",
        algorithm_status=ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Landowner and other private big-game permit categories are target-scope inventory items but excluded from predictive public draw modeling.",
    ),
    StrategySpec(
        draw_system_type="MITIGATION_OR_DEPREDATION_BIG_GAME",
        module_name="engine.utah_draw_predictive.exclusions",
        algorithm_status=ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Mitigation and depredation big-game categories are excluded from predictive public draw modeling.",
    ),
    StrategySpec(
        draw_system_type="OUT_OF_SCOPE_NON_TARGET",
        module_name="engine.utah_draw_predictive.exclusions",
        algorithm_status=ALGORITHM_STATUS_OUT_OF_SCOPE_NON_TARGET,
        target_scope=TARGET_SCOPE_OUT_OF_SCOPE,
        reason="This category is outside the approved predictive-engine universe.",
    ),
    StrategySpec(
        draw_system_type="UNKNOWN_TARGET",
        module_name="engine.utah_draw_predictive.exclusions",
        algorithm_status=ALGORITHM_STATUS_UNKNOWN_TARGET_NEEDS_REVIEW,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Target-scope category could not be resolved to a supported draw-system family.",
    ),
]
