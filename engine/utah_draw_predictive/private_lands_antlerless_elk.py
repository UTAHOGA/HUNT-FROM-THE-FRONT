"""Private-lands-only antlerless elk allocation strategy declaration."""

from __future__ import annotations

from . import ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING, StrategySpec, TARGET_SCOPE_TARGET


STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type="PRIVATE_LANDS_ONLY_ANTLERLESS_ELK",
        module_name="engine.utah_draw_predictive.private_lands_antlerless_elk",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Private-lands-only antlerless elk is in scope and should use an allocation/availability strategy, not a preference-draw probability model.",
        legacy_logic_present=True,
    ),
]
