from engine.utah_bonus_predictive.backtest import brier_score, mean_absolute_error


def test_backtest_smoke() -> None:
    assert round(mean_absolute_error([10, 20], [12, 17]), 3) == 2.5
    assert round(brier_score([1, 0], [0.8, 0.2]), 3) == 0.04

