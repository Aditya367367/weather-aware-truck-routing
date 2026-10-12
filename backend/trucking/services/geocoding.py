"""Place search (type-ahead) via Photon, which permits autocomplete usage."""
from __future__ import annotations

from dataclasses import dataclass

from django.core.cache import cache

from .http import Http


@dataclass(frozen=True)
class GeoResult:
    label: str
    lat: float
    lng: float


class PhotonGeocoder:
    def __init__(self, http: Http, url: str, limit: int = 6):
        self._http, self._url, self._limit = http, url, limit

    def search(self, query: str) -> list[GeoResult]:
        key = f"geo:{query.strip().lower()}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        body = self._http.get_json(self._url, {"q": query, "limit": self._limit, "lang": "en"})
        results = [r for r in map(self._parse, body.get("features", [])) if r]
        cache.set(key, results, 3600)
        return results

    @staticmethod
    def _parse(feature: dict) -> GeoResult | None:
        p, coords = feature.get("properties", {}), feature.get("geometry", {}).get("coordinates")
        if not coords:
            return None
        parts = [p.get("name"), p.get("street"), p.get("city"), p.get("state"), p.get("country")]
        label = ", ".join(dict.fromkeys(x for x in parts if x))  # de-duplicated, order preserved
        return GeoResult(label=label, lat=coords[1], lng=coords[0])
