"""Target-scope general big-game strategies that are not yet modeled."""

from __future__ import annotations

from . import ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING, StrategySpec, TARGET_SCOPE_TARGET


STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type="GENERAL_BIG_GAME_OTHER",
        module_name="engine.utah_draw_predictive.youth",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="This is a target-scope big-game draw category, but it does not have an accepted production predictive strategy yet.",
        legacy_logic_present=True,
    ),
]
