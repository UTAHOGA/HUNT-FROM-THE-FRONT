"""Random-only and remaining-permit target-scope strategy declarations."""

from __future__ import annotations

from . import ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW, ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING, StrategySpec, TARGET_SCOPE_TARGET


STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type="BEAR_DRAW",
        module_name="engine.utah_draw_predictive.random_only",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Bear remains target-scope, but no accepted production predictive bear strategy has been proven yet.",
        legacy_logic_present=True,
    ),
    StrategySpec(
        draw_system_type="MOUNTAIN_LION_DRAW",
        module_name="engine.utah_draw_predictive.random_only",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Mountain lion/cougar remains target-scope, but no accepted production predictive lion strategy has been proven yet.",
        legacy_logic_present=True,
    ),
    StrategySpec(
        draw_system_type="RANDOM_ONLY_TARGET",
        module_name="engine.utah_draw_predictive.random_only",
        algorithm_status=ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW,
        target_scope=TARGET_SCOPE_TARGET,
        reason="This target-scope category is random-only and is excluded from the current predictive draw engine.",
    ),
    StrategySpec(
        draw_system_type="OTC_OR_REMAINING_TARGET",
        module_name="engine.utah_draw_predictive.random_only",
        algorithm_status=ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW,
        target_scope=TARGET_SCOPE_TARGET,
        reason="OTC, remaining-permit, conservation, expo, and sportsman target-scope categories are excluded from predictive draw-odds modeling.",
    ),
]
