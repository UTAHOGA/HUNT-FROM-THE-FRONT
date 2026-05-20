"""Dedicated Hunter strategy declarations."""

from __future__ import annotations

from . import ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING, StrategySpec, TARGET_SCOPE_TARGET


STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type="PREFERENCE_DEDICATED_HUNTER_DEER",
        module_name="engine.utah_draw_predictive.dedicated_hunter",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Dedicated Hunter deer remains target-scope but has not been promoted to an accepted production preference engine.",
        legacy_logic_present=True,
    ),
]
