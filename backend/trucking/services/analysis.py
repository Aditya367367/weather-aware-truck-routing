"""Orchestrates routing -> checkpoints/ETAs -> weather -> risk -> scoring -> heatmap."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..domain.geo import LatLng, Polyline, distance_marks, snap
from ..domain.risk import Assessment, Weather, assess
from ..domain.scoring import RouteScore, explain, rank, score_route
from .routing import RouteOption, RoutingProvider
from .weather import WeatherProvider

ROUTE_COUNT = 3
FORECAST_HOURS = 48
HEAT_GRID_DEG = 0.05


@dataclass(frozen=True)
class Place:
    lat: float
    lng: float
    label: str = ""

    @property
    def latlng(self) -> LatLng:
        return (self.lat, self.lng)


@dataclass(frozen=True)
class TripRequest:
    origin: Place
    destination: Place
    departure: datetime  # tz-aware
    weight_lb: int
    interval_mi: int


@dataclass(frozen=True)
class Checkpoint:
    index: int
    mile: float
    point: LatLng
    eta: datetime
    weather: Weather
    assessment: Assessment


@dataclass(frozen=True)
class RouteAnalysis:
    id: str
    polyline: Polyline
    distance_mi: float
    duration_s: float
    arrival: datetime
    checkpoints: list[Checkpoint]
    score: RouteScore


@dataclass(frozen=True)
class HeatPoint:
    point: LatLng
    levels: list[int]  # risk level for each forecast hour 0..FORECAST_HOURS


@dataclass(frozen=True)
class TripAnalysis:
    request: TripRequest
    routes: list[RouteAnalysis]
    ranking: list[str]  # route ids, best first
    reason: str
    advisory: str | None
    heatmap: list[HeatPoint]


@dataclass(frozen=True)
class _Plan:
    option: RouteOption
    marks: list[float]
    points: list[LatLng]
    etas: list[datetime]


class TripAnalyzer:
    def __init__(self, router: RoutingProvider, weather: WeatherProvider):
        self._router, self._weather = router, weather

    def analyze(self, req: TripRequest) -> TripAnalysis:
        options = self._router.routes(req.origin.latlng, req.destination.latlng, ROUTE_COUNT)
        plans = [self._plan(o, req) for o in options]

        # One weather fetch for every checkpoint of every route; it also feeds the heatmap.
        all_points = [pt for p in plans for pt in p.points]
        window_end = max(req.departure + timedelta(hours=FORECAST_HOURS), *(p.etas[-1] for p in plans)) + timedelta(hours=1)
        series = self._weather.fetch(all_points, req.departure, window_end)

        routes, cursor = [], 0
        for n, plan in enumerate(plans, start=1):
            chunk = series[cursor : cursor + len(plan.points)]
            cursor += len(plan.points)
            routes.append(self._analyze_route(f"r{n}", plan, chunk, req))

        scores = [r.score for r in routes]
        order = rank(scores)
        best, runner_up = order[0], (order[1] if len(order) > 1 else None)
        advisory = None
        if scores[best].no_travel_miles > 0:
            advisory = "Every route crosses No Travel conditions at this departure time. Consider delaying or rerouting."

        return TripAnalysis(
            request=req,
            routes=routes,
            ranking=[routes[i].id for i in order],
            reason=explain(scores[best], scores[runner_up] if runner_up is not None else None),
            advisory=advisory,
            heatmap=self._heatmap(all_points, series, req),
        )

    @staticmethod
    def _plan(option: RouteOption, req: TripRequest) -> _Plan:
        poly = option.polyline
        # Marks are in real road miles (the provider's distance), so "every 25 mi" is true and the last
        # checkpoint equals the route length. The simplified geometry is a bit shorter, hence the rescale.
        marks = distance_marks(option.distance_mi, req.interval_mi)
        to_geometry = poly.length_mi / option.distance_mi
        return _Plan(
            option=option,
            marks=marks,
            points=[poly.point_at(m * to_geometry) for m in marks],
            etas=[req.departure + timedelta(seconds=option.duration_s * m / option.distance_mi) for m in marks],
        )

    @staticmethod
    def _analyze_route(route_id: str, plan: _Plan, series, req: TripRequest) -> RouteAnalysis:
        checkpoints = []
        for i, (mile, point, eta, s) in enumerate(zip(plan.marks, plan.points, plan.etas, series)):
            weather = s.at(eta)
            checkpoints.append(Checkpoint(i, mile, point, eta, weather, assess(weather, req.weight_lb)))
        score = score_route([c.assessment.level for c in checkpoints], plan.marks, plan.option.duration_s)
        return RouteAnalysis(
            id=route_id,
            polyline=plan.option.polyline,
            distance_mi=plan.option.distance_mi,
            duration_s=plan.option.duration_s,
            arrival=plan.etas[-1],
            checkpoints=checkpoints,
            score=score,
        )

    @staticmethod
    def _heatmap(points: list[LatLng], series, req: TripRequest) -> list[HeatPoint]:
        unique: dict[LatLng, tuple[LatLng, object]] = {}
        for pt, s in zip(points, series):
            unique.setdefault(snap(pt, HEAT_GRID_DEG), (pt, s))
        hours = [req.departure + timedelta(hours=h) for h in range(FORECAST_HOURS + 1)]
        return [
            HeatPoint(pt, [int(assess(s.at(t), req.weight_lb).level) for t in hours]) for pt, s in unique.values()
        ]
