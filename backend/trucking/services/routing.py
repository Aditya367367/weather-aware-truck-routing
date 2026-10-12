"""Routing via OSRM (no API key, no routing engine of our own)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

from ..domain.geo import LatLng, Polyline, bearing, offset
from ..errors import NoRouteError, UpstreamError
from .http import Http

METERS_PER_MILE = 1609.344


@dataclass(frozen=True)
class RouteOption:
    polyline: Polyline
    distance_mi: float
    duration_s: float


class RoutingProvider(Protocol):
    def routes(self, origin: LatLng, destination: LatLng, count: int) -> list[RouteOption]: ...


class OsrmRouting:
    MAX_DETOUR_RATIO = 1.6  # reject alternatives much longer than the best route
    MAX_OVERLAP = 0.85  # reject alternatives that mostly retrace an existing route
    MAX_RETRACED_MI = 5  # reject routes that drive out to the via-point and straight back (dead-end spurs)
    # (position along the best route, side of the O->D axis as a bearing offset, detour size as a fraction of route length)
    DETOUR_PROBES = (
        (0.50, 90, 0.12), (0.50, -90, 0.12), (0.50, 90, 0.25), (0.50, -90, 0.25),
        (0.35, 90, 0.15), (0.35, -90, 0.15), (0.65, 90, 0.15), (0.65, -90, 0.15),
    )

    def __init__(self, http: Http, base_url: str, time_factor: float = 1.0):
        self._http, self._base, self._time_factor = http, base_url.rstrip("/"), time_factor

    def routes(self, origin: LatLng, destination: LatLng, count: int = 3) -> list[RouteOption]:
        found = self._request([origin, destination], alternatives=count)
        if len(found) < count:
            found += self._detours(origin, destination, found, count - len(found))
        return found[:count]

    # -- internals ---------------------------------------------------------
    def _request(self, waypoints: list[LatLng], alternatives: int) -> list[RouteOption]:
        coords = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in waypoints)
        body = self._http.get_json(
            f"{self._base}/route/v1/driving/{coords}",
            {
                "alternatives": str(alternatives) if alternatives > 1 else "false",
                "overview": "simplified",
                "geometries": "geojson",
                "steps": "false",
            },
        )
        code = body.get("code")
        if code in ("NoRoute", "NoSegment"):
            raise NoRouteError()
        if code != "Ok":
            raise UpstreamError(f"Routing provider error: {body.get('message', code)}")
        return [
            RouteOption(
                polyline=Polyline([(lat, lng) for lng, lat in r["geometry"]["coordinates"]]),
                distance_mi=r["distance"] / METERS_PER_MILE,
                duration_s=r["duration"] * self._time_factor,
            )
            for r in body["routes"]
        ]

    def _detours(self, origin: LatLng, destination: LatLng, found: list[RouteOption], needed: int) -> list[RouteOption]:
        """Top up with routes forced through a via-point beside the best route (best effort, probed in parallel)."""
        best = found[0]
        axis = bearing(origin, destination)

        def probe(spec: tuple[float, int, float]) -> RouteOption | None:
            along, side, scale = spec
            anchor = best.polyline.point_at(best.polyline.length_mi * along)
            via = offset(anchor, axis + side, min(best.distance_mi * scale, 80))
            try:
                return self._request([origin, via, destination], alternatives=1)[0]
            except (NoRouteError, UpstreamError):
                return None  # an optional extra route must never fail the whole request

        with ThreadPoolExecutor(max_workers=4) as pool:
            candidates = [c for c in pool.map(probe, self.DETOUR_PROBES) if c]

        taken = [f.polyline.cells() for f in found]
        extra: list[RouteOption] = []
        for candidate in candidates:  # probe order = preference order
            if len(extra) == needed:
                break
            cells = candidate.polyline.cells()
            if (
                candidate.distance_mi <= best.distance_mi * self.MAX_DETOUR_RATIO
                and candidate.polyline.retraced_mi() <= self.MAX_RETRACED_MI
                and all(len(cells & t) / len(cells) < self.MAX_OVERLAP for t in taken)
            ):
                extra.append(candidate)
                taken.append(cells)
        return extra
