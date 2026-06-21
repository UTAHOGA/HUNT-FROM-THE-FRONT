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
        module_name="engine.utah_draw_predictive.special_bonus",
        algorithm_status=ALGORITHM_STATUS_MODELED_BONUS,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Public CWMU big-game permits use the Utah bonus model and only promote rows with proven public-draw source data, valid quota, and modeled bonus probabilities.",
        legacy_logic_present=True,
        modeled_by_engine=True,
    ),
    StrategySpec(
        draw_system_type="BONUS_ANTLERLESS_MOOSE",
        module_name="engine.utah_draw_predictive.special_bonus",
        algorithm_status=ALGORITHM_STATUS_MODELED_BONUS,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Antlerless moose uses the Utah bonus model and only promotes rows with valid source history, forecast quota, and modeled bonus probabilities.",
        legacy_logic_present=True,
        modeled_by_engine=True,
    ),
    StrategySpec(
        draw_system_type="BONUS_EWE_BIGHORN",
        module_name="engine.utah_draw_predictive.special_bonus",
        algorithm_status=ALGORITHM_STATUS_MODELED_BONUS,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Ewe bighorn uses the Utah bonus model and only promotes rows with valid source history, forecast quota, and modeled bonus probabilities.",
        legacy_logic_present=True,
        modeled_by_engine=True,
    ),
    StrategySpec(
        draw_system_type="BONUS_TURKEY",
        module_name="engine.utah_draw_predictive.turkey",
        algorithm_status=ALGORITHM_STATUS_MODELED_BONUS,
        target_scope=TARGET_SCOPE_TARGET,
        reason="Limited-entry turkey uses the Utah bonus model and only promotes rows with proven public-draw source data, valid quota, and modeled bonus probabilities.",
        legacy_logic_present=True,
        modeled_by_engine=True,
    ),
]
