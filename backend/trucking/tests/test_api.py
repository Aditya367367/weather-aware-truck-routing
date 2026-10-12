"""End-to-end through the HTTP layer with fake providers (no network)."""
from datetime import datetime, timedelta, timezone

import pytest
from rest_framework.test import APIClient

from trucking import views
from trucking.domain.geo import Polyline
from trucking.services.analysis import TripAnalyzer
from trucking.services.routing import RouteOption
from trucking.services.weather import HourlySeries


class FakeRouter:
    def routes(self, o, d, count):
        def line(lat_shift):  # three roughly parallel eastbound routes
            return Polyline([(o[0] + lat_shift, o[1]), (d[0] + lat_shift, d[1])])
        return [RouteOption(line(s), 300.0, 18_000.0 + i * 600) for i, s in enumerate((0, 0.5, -0.5))]


class FakeWeather:
    """Strong wind everywhere on the northern-most route, calm elsewhere."""
    def fetch(self, points, start, end):
        hours = int((end - start).total_seconds() // 3600) + 48
        t0 = start.replace(minute=0, second=0, microsecond=0)
        mk = lambda wind: HourlySeries(t0, (wind,) * hours, (0.0,) * hours, (0.0,) * hours)  # noqa: E731
        return [mk(50.0 if p[0] > 40.2 else 5.0) for p in points]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(views, "get_analyzer", lambda: TripAnalyzer(FakeRouter(), FakeWeather()))
    return APIClient()


def body(**over):
    base = {
        "origin": {"lat": 40.0, "lng": -100.0, "label": "A"},
        "destination": {"lat": 40.0, "lng": -94.0, "label": "B"},
        "departure_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "load_weight_lb": 42_000,
        "interval_miles": 25,
    }
    return {**base, **over}


def test_analyze_returns_three_routes_heatmap_and_recommendation(client):
    r = client.post("/api/routes/analyze", body(), format="json")
    assert r.status_code == 200
    data = r.json()
    assert len(data["routes"]) == 3
    assert data["heatmap"]["hours"] == 48 and len(data["heatmap"]["points"][0]["levels"]) == 49
    chosen = next(x for x in data["routes"] if x["id"] == data["recommended_route_id"])
    assert chosen["summary"]["severe_miles"] == 0 and chosen["summary"]["no_travel_miles"] == 0
    assert chosen["checkpoints"][-1]["mile"] == chosen["distance_mi"]  # checkpoints use real road miles
    first = chosen["checkpoints"][0]
    assert first["mile"] == 0 and {"eta", "level", "wind_mph"} <= first.keys()


def test_load_rule_applied_through_api(client):
    heavy = client.post("/api/routes/analyze", body(load_weight_lb=42_000), format="json").json()
    northern = next(x for x in heavy["routes"] if x["checkpoints"][0]["lat"] > 40.2)
    assert northern["summary"]["no_travel_miles"] > 0  # 50 mph wind + >30k lb


@pytest.mark.parametrize("override", [
    {"load_weight_lb": 120_000}, {"interval_miles": 7},
    {"departure_time": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()},
    {"destination": {"lat": 40.0, "lng": -100.0}},
])
def test_validation_errors(client, override):
    assert client.post("/api/routes/analyze", body(**override), format="json").status_code == 400
