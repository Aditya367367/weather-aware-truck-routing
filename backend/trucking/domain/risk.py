"""Weather risk classification. Single source of truth for thresholds and load rules."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Risk(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


@dataclass(frozen=True)
class Weather:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


# (threshold, level, strictly_greater). Checked top-down; first match wins.
# Range edges shared by two bands (e.g. rain 0.25) resolve to the HIGHER band,
# except the open-ended No Travel bands for rain/snow, which are strictly ">".
_BANDS: dict[str, tuple[tuple[float, Risk, bool], ...]] = {
    "wind": ((55, Risk.NO_TRAVEL, False), (45, Risk.SEVERE, False), (35, Risk.HIGH, False), (25, Risk.MODERATE, False)),
    "rain": ((1.00, Risk.NO_TRAVEL, True), (0.50, Risk.SEVERE, False), (0.25, Risk.HIGH, False), (0.10, Risk.MODERATE, False)),
    "snow": ((3.0, Risk.NO_TRAVEL, True), (2.0, Risk.SEVERE, False), (1.0, Risk.HIGH, False), (0.5, Risk.MODERATE, False)),
}

# (wind_min_inclusive, wind_max_exclusive, weight_over_lb, resulting_floor)
_LOAD_RULES: tuple[tuple[float, float, int, Risk], ...] = (
    (45, 55, 30_000, Risk.NO_TRAVEL),
    (35, 45, 40_000, Risk.SEVERE),
)


def classify(condition: str, value: float) -> Risk:
    for threshold, level, strict in _BANDS[condition]:
        if (value > threshold) if strict else (value >= threshold):
            return level
    return Risk.LOW


def apply_load_rules(wind_mph: float, weight_lb: float, level: Risk) -> Risk:
    for lo, hi, over_lb, floor in _LOAD_RULES:
        if lo <= wind_mph < hi and weight_lb > over_lb:
            return max(level, floor)
    return level


@dataclass(frozen=True)
class Assessment:
    level: Risk
    by_condition: dict[str, Risk]  # wind is load-adjusted
    drivers: tuple[str, ...]  # conditions responsible for `level`
    load_adjusted: bool  # True when the load rules raised the wind level


def assess(weather: Weather, weight_lb: float) -> Assessment:
    wind_base = classify("wind", weather.wind_mph)
    wind = apply_load_rules(weather.wind_mph, weight_lb, wind_base)
    by_condition = {
        "wind": wind,
        "rain": classify("rain", weather.rain_in_hr),
        "snow": classify("snow", weather.snow_in_hr),
    }
    level = max(by_condition.values())
    drivers = tuple(c for c, r in by_condition.items() if r == level and level > Risk.LOW)
    return Assessment(level, by_condition, drivers, load_adjusted=wind > wind_base)
