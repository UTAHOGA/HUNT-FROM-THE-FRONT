"""Bonus draw strategy declarations for target-scope Utah categories."""

from __future__ import annotations

from . import ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING, ALGORITHM_STATUS_MODELED_BONUS, StrategySpec, TARGET_SCOPE_TARGET


STRATEGY_SPECS = [
    StrategySpec(
        draw_system_type="BONUS_OIL_BIG_GAME",
        module_name="engine.utah_bonus_predictive",
        algorithm_status=ALGORITHM_STATUS_MODELED_BONUS,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Modeled by the accepted Utah bonus predictive engine.",
        modeled_by_engine=True,
    ),
    StrategySpec(
        draw_system_type="BONUS_LE_BIG_GAME",
        module_name="engine.utah_bonus_predictive",
        algorithm_status=ALGORITHM_STATUS_MODELED_BONUS,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Modeled by the accepted Utah bonus predictive engine.",
        modeled_by_engine=True,
    ),
    StrategySpec(
        draw_system_type="BONUS_PLE_BIG_GAME",
        module_name="engine.utah_bonus_predictive",
        algorithm_status=ALGORITHM_STATUS_MODELED_BONUS,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Modeled by the accepted Utah bonus predictive engine.",
        modeled_by_engine=True,
    ),
    StrategySpec(
        draw_system_type="BONUS_CWMU_BIG_GAME",
        module_name="engine.utah_draw_predictive.bonus",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="CWMU public big-game permits are target-scope, but no accepted production bonus strategy is implemented yet.",
        legacy_logic_present=True,
    ),
    StrategySpec(
        draw_system_type="BONUS_ANTLERLESS_MOOSE",
        module_name="engine.utah_draw_predictive.bonus",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Antlerless moose is a target-scope bonus category, but it is not yet covered by a category-correct accepted production strategy.",
        legacy_logic_present=True,
    ),
    StrategySpec(
        draw_system_type="BONUS_EWE_BIGHORN",
        module_name="engine.utah_draw_predictive.bonus",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Ewe bighorn is a target-scope bonus category, but it is not yet covered by a category-correct accepted production strategy.",
        legacy_logic_present=True,
    ),
    StrategySpec(
        draw_system_type="BONUS_TURKEY",
        module_name="engine.utah_draw_predictive.bonus",
        algorithm_status=ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Turkey remains target-scope, but a production predictive turkey strategy has not been accepted yet.",
        legacy_logic_present=True,
    ),
]
