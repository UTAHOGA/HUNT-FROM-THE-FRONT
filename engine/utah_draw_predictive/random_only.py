"""Random-only and remaining-permit target-scope strategy declarations."""

from __future__ import annotations

from . import ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW, StrategySpec, TARGET_SCOPE_TARGET


STRATEGY_SPECS = [
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
