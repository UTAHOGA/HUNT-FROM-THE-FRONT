from engine.utah_bonus_predictive.split import split_utah_bonus_permits


def test_split_zero() -> None:
    out = split_utah_bonus_permits(0)
    assert out.maxPointPermits == 0
    assert out.randomPermits == 0


def test_split_one_random_only() -> None:
    out = split_utah_bonus_permits(1)
    assert out.maxPointPermits == 0
    assert out.randomPermits == 1
    assert out.randomOnly is True


def test_split_seven() -> None:
    out = split_utah_bonus_permits(7)
    assert out.maxPointPermits == 4
    assert out.randomPermits == 3


def test_split_nine() -> None:
    out = split_utah_bonus_permits(9)
    assert out.maxPointPermits == 5
    assert out.randomPermits == 4

