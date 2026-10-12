import pytest

from trucking.domain.risk import Risk, Weather, assess, classify


@pytest.mark.parametrize(
    "cond,value,expected",
    [
        ("wind", 24.9, Risk.LOW), ("wind", 25, Risk.MODERATE), ("wind", 34.9, Risk.MODERATE),
        ("wind", 35, Risk.HIGH), ("wind", 45, Risk.SEVERE), ("wind", 54.9, Risk.SEVERE), ("wind", 55, Risk.NO_TRAVEL),
        ("rain", 0.09, Risk.LOW), ("rain", 0.10, Risk.MODERATE), ("rain", 0.25, Risk.HIGH),
        ("rain", 0.50, Risk.SEVERE), ("rain", 1.00, Risk.SEVERE), ("rain", 1.01, Risk.NO_TRAVEL),
        ("snow", 0.49, Risk.LOW), ("snow", 0.5, Risk.MODERATE), ("snow", 1.0, Risk.HIGH),
        ("snow", 2.0, Risk.SEVERE), ("snow", 3.0, Risk.SEVERE), ("snow", 3.01, Risk.NO_TRAVEL),
    ],
)
def test_thresholds(cond, value, expected):
    assert classify(cond, value) == expected


@pytest.mark.parametrize(
    "wind,weight,expected",
    [
        (60, 1_000, Risk.NO_TRAVEL),       # >=55 -> No Travel for any load
        (50, 30_001, Risk.NO_TRAVEL),      # 45-54 + >30k
        (50, 30_000, Risk.SEVERE),         # boundary: not strictly over 30k
        (40, 40_001, Risk.SEVERE),         # 35-44 + >40k raises High -> Severe
        (40, 40_000, Risk.HIGH),
        (30, 79_000, Risk.MODERATE),       # load rules only apply to high wind
    ],
)
def test_load_rules(wind, weight, expected):
    assert assess(Weather(wind, 0, 0), weight).level == expected


def test_worst_condition_wins_and_is_reported():
    a = assess(Weather(10, 0.6, 1.2), 20_000)
    assert a.level == Risk.SEVERE and a.drivers == ("rain",) and not a.load_adjusted


def test_load_adjustment_flag():
    a = assess(Weather(40, 0, 0), 45_000)
    assert a.load_adjusted and a.drivers == ("wind",)
