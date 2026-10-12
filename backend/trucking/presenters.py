"""Domain objects -> JSON-ready dicts (the API contract lives here)."""
from __future__ import annotations

from .domain.risk import Risk
from .services.analysis import FORECAST_HOURS, Checkpoint, HeatPoint, RouteAnalysis, TripAnalysis


def _checkpoint(c: Checkpoint) -> dict:
    return {
        "index": c.index,
        "mile": round(c.mile, 1),
        "lat": round(c.point[0], 5),
        "lng": round(c.point[1], 5),
        "eta": c.eta.isoformat(),
        "level": int(c.assessment.level),
        "label": c.assessment.level.label,
        "drivers": list(c.assessment.drivers),
        "load_adjusted": c.assessment.load_adjusted,
        "wind_mph": round(c.weather.wind_mph, 1),
        "rain_in_hr": round(c.weather.rain_in_hr, 2),
        "snow_in_hr": round(c.weather.snow_in_hr, 2),
    }


def _route(r: RouteAnalysis) -> dict:
    s = r.score
    return {
        "id": r.id,
        "distance_mi": round(r.distance_mi, 1),
        "duration_s": round(r.duration_s),
        "arrival": r.arrival.isoformat(),
        "geometry": [[round(lng, 5), round(lat, 5)] for lat, lng in r.polyline.points],  # GeoJSON order
        "summary": {
            "no_travel_miles": round(s.no_travel_miles, 1),
            "severe_miles": round(s.severe_miles, 1),
            "high_miles": round(s.high_miles, 1),
            "moderate_miles": round(s.moderate_miles, 1),
            "low_miles": round(max(r.distance_mi - s.no_travel_miles - s.severe_miles - s.high_miles - s.moderate_miles, 0), 1),
            "avg_risk": round(s.avg_risk, 2),
            "max_level": int(s.max_risk),
            "max_label": Risk(s.max_risk).label,
        },
        "checkpoints": [_checkpoint(c) for c in r.checkpoints],
    }


def _heat(h: HeatPoint) -> dict:
    return {"lat": round(h.point[0], 4), "lng": round(h.point[1], 4), "levels": h.levels}


def present(a: TripAnalysis) -> dict:
    return {
        "departure_time": a.request.departure.isoformat(),
        "load_weight_lb": a.request.weight_lb,
        "interval_miles": a.request.interval_mi,
        "recommended_route_id": a.ranking[0],
        "ranking": a.ranking,
        "reason": a.reason,
        "advisory": a.advisory,
        "routes": [_route(r) for r in a.routes],
        "heatmap": {"hours": FORECAST_HOURS, "points": [_heat(h) for h in a.heatmap]},
    }
