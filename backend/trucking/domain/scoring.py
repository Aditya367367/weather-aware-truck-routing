"""Route scoring and ranking: Severe miles > High miles > average risk > travel time."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .risk import Risk


def coverage_miles(marks: Sequence[float]) -> list[float]:
    """Miles of road each checkpoint represents: halfway to its neighbours (route ends clamp)."""
    total = marks[-1]
    out = []
    for i, m in enumerate(marks):
        start = 0.0 if i == 0 else (marks[i - 1] + m) / 2
        end = total if i == len(marks) - 1 else (m + marks[i + 1]) / 2
        out.append(end - start)
    return out


@dataclass(frozen=True)
class RouteScore:
    no_travel_miles: float
    severe_miles: float
    high_miles: float
    moderate_miles: float
    avg_risk: float  # mile-weighted mean of Risk values (0-4)
    max_risk: Risk
    duration_s: float

    @property
    def sort_key(self) -> tuple[float, ...]:
        # Rounded so float noise never decides a ranking.
        return (
            round(self.no_travel_miles, 1),
            round(self.severe_miles, 1),
            round(self.high_miles, 1),
            round(self.avg_risk, 1),  # <0.1 on the 0-4 scale counts as a tie
            round(self.duration_s / 60),
        )


def score_route(levels: Sequence[Risk], marks: Sequence[float], duration_s: float) -> RouteScore:
    miles = coverage_miles(marks)
    by_level = {r: 0.0 for r in Risk}
    for level, m in zip(levels, miles):
        by_level[level] += m
    total = sum(miles) or 1.0
    return RouteScore(
        no_travel_miles=by_level[Risk.NO_TRAVEL],
        severe_miles=by_level[Risk.SEVERE],
        high_miles=by_level[Risk.HIGH],
        moderate_miles=by_level[Risk.MODERATE],
        avg_risk=sum(int(r) * m for r, m in by_level.items()) / total,
        max_risk=max(levels),
        duration_s=duration_s,
    )


def rank(scores: Sequence[RouteScore]) -> list[int]:
    """Indices of `scores`, best first (stable for ties)."""
    return sorted(range(len(scores)), key=lambda i: scores[i].sort_key)


_CRITERIA = (
    ("No Travel miles", lambda s: f"{s.no_travel_miles:.0f} mi"),
    ("Severe miles", lambda s: f"{s.severe_miles:.0f} mi"),
    ("High-risk miles", lambda s: f"{s.high_miles:.0f} mi"),
    ("average risk", lambda s: f"{s.avg_risk:.2f}"),
    ("travel time", lambda s: f"{s.duration_s / 3600:.1f} h"),
)


def explain(best: RouteScore, runner_up: RouteScore | None) -> str:
    """Human-readable reason, naming the first criterion that separates the winner."""
    if runner_up is None:
        return "Only one route was available."
    for (name, fmt), a, b in zip(_CRITERIA, best.sort_key, runner_up.sort_key):
        if a != b:
            return f"Lowest {name}: {fmt(best)} vs {fmt(runner_up)} on the next-best route."
    return "Routes are equivalent on weather risk and travel time."
