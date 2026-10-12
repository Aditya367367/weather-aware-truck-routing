"""Pure geometry helpers. Coordinates are (lat, lng) tuples."""
from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Sequence

EARTH_RADIUS_MI = 3958.7613
LatLng = tuple[float, float]


def haversine_mi(a: LatLng, b: LatLng) -> float:
    lat1, lng1 = map(math.radians, a)
    lat2, lng2 = map(math.radians, b)
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def snap(point: LatLng, grid_deg: float) -> LatLng:
    """Snap to a regular grid so near-identical points share one weather lookup."""
    return (round(round(point[0] / grid_deg) * grid_deg, 4), round(round(point[1] / grid_deg) * grid_deg, 4))


def offset(point: LatLng, bearing_deg: float, miles: float) -> LatLng:
    """Point reached travelling `miles` from `point` on an initial bearing."""
    lat1, lng1 = map(math.radians, point)
    brg, d = math.radians(bearing_deg), miles / EARTH_RADIUS_MI
    lat2 = math.asin(math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(brg))
    lng2 = lng1 + math.atan2(math.sin(brg) * math.sin(d) * math.cos(lat1), math.cos(d) - math.sin(lat1) * math.sin(lat2))
    return (math.degrees(lat2), math.degrees(lng2))


def bearing(a: LatLng, b: LatLng) -> float:
    lat1, lng1 = map(math.radians, a)
    lat2, lng2 = map(math.radians, b)
    y = math.sin(lng2 - lng1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lng2 - lng1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def distance_marks(length_mi: float, step_mi: float) -> list[float]:
    """0, step, 2*step ... up to `length_mi`, always ending exactly at `length_mi`."""
    marks = [i * step_mi for i in range(int(length_mi // step_mi) + 1)]
    if length_mi - marks[-1] > 1e-6:
        marks.append(length_mi)
    return marks


class Polyline:
    """Immutable polyline; point-at-distance in O(log n)."""

    def __init__(self, points: Sequence[LatLng]):
        if len(points) < 2:
            raise ValueError("A polyline needs at least two points")
        self.points: tuple[LatLng, ...] = tuple(points)
        cum = [0.0]
        for a, b in zip(self.points, self.points[1:]):
            cum.append(cum[-1] + haversine_mi(a, b))
        self._cum = cum

    @property
    def length_mi(self) -> float:
        return self._cum[-1]

    def point_at(self, miles: float) -> LatLng:
        miles = min(max(miles, 0.0), self.length_mi)
        i = min(bisect_right(self._cum, miles) - 1, len(self.points) - 2)
        seg = self._cum[i + 1] - self._cum[i]
        t = 0.0 if seg == 0 else (miles - self._cum[i]) / seg
        (lat1, lng1), (lat2, lng2) = self.points[i], self.points[i + 1]
        return (lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t)

    def retraced_mi(self, step_mi: float = 1.0, cell_deg: float = 0.01) -> float:
        """Approximate miles driven over ground already covered (out-and-back spurs, U-turns)."""
        cells = [snap(self.point_at(m), cell_deg) for m in distance_marks(self.length_mi, step_mi)]
        return (len(cells) - len(set(cells))) * step_mi

    def cells(self, step_mi: float = 2.0, cell_deg: float = 0.02) -> set[LatLng]:
        """Coarse occupancy set, used to measure overlap between routes."""
        return {snap(self.point_at(m), cell_deg) for m in distance_marks(self.length_mi, step_mi)}
