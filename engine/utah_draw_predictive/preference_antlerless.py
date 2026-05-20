"""Preference draw strategy declarations for Utah antlerless systems."""

from __future__ import annotations

from . import ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING, StrategySpec, TARGET_SCOPE_TARGET


STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type="PREFERENCE_ANTLERLESS_DEER",
        module_name="engine.utah_draw_predictive.preference_antlerless",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Antlerless deer requires a real preference strategy and must not reuse the OIL/LE/PLE bonus model.",
        legacy_logic_present=True,
    ),
    StrategySpec(
        draw_system_type="PREFERENCE_ANTLERLESS_ELK",
        module_name="engine.utah_draw_predictive.preference_antlerless",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Antlerless elk requires a real preference strategy and must not reuse the OIL/LE/PLE bonus model.",
        legacy_logic_present=True,
    ),
    StrategySpec(
        draw_system_type="PREFERENCE_DOE_PRONGHORN",
        module_name="engine.utah_draw_predictive.preference_antlerless",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Doe pronghorn requires a real preference strategy and must not reuse the OIL/LE/PLE bonus model.",
        legacy_logic_present=True,
    ),
]
