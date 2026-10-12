"""Hourly weather via Open-Meteo (free, keyless, batched, up to 16 days ahead)."""
from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from django.core.cache import cache

from ..domain.geo import LatLng, snap
from ..domain.risk import Weather
from ..errors import ForecastUnavailableError, UpstreamError
from .http import Http

MAX_FORECAST_DAYS = 15  # Open-Meteo serves today .. today+15
BATCH_SIZE = 50
CACHE_TTL_S = 30 * 60


@dataclass(frozen=True)
class HourlySeries:
    start: datetime  # UTC, first hourly sample
    wind_mph: tuple[float, ...]
    rain_in: tuple[float, ...]
    snow_in: tuple[float, ...]

    def at(self, when: datetime) -> Weather:
        """Nearest-hour sample (clamped to the series bounds)."""
        i = round((when - self.start).total_seconds() / 3600)
        i = min(max(i, 0), len(self.wind_mph) - 1)
        return Weather(self.wind_mph[i], self.rain_in[i], self.snow_in[i])


class WeatherProvider(Protocol):
    def fetch(self, points: Sequence[LatLng], start: datetime, end: datetime) -> list[HourlySeries]:
        """One series per input point (same order), covering at least [start, end]."""
        ...


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


class OpenMeteoWeather:
    def __init__(self, http: Http, url: str, grid_deg: float = 0.05, workers: int = 4):
        self._http, self._url, self._grid, self._workers = http, url, grid_deg, workers

    def fetch(self, points: Sequence[LatLng], start: datetime, end: datetime) -> list[HourlySeries]:
        start_d, end_d = start.astimezone(timezone.utc).date(), end.astimezone(timezone.utc).date()
        today = datetime.now(timezone.utc).date()
        if end_d > today + timedelta(days=MAX_FORECAST_DAYS):
            raise ForecastUnavailableError(
                f"Forecast covers {MAX_FORECAST_DAYS} days ahead; this trip's window ends {end_d.isoformat()}."
            )

        keys = [snap(p, self._grid) for p in points]  # many checkpoints collapse onto shared cells
        unique = list(dict.fromkeys(keys))
        cache_key = lambda k: f"om:{k[0]}:{k[1]}:{start_d}:{end_d}"  # noqa: E731
        by_cache_key = {cache_key(k): k for k in unique}
        series: dict[LatLng, HourlySeries] = {by_cache_key[ck]: v for ck, v in cache.get_many(list(by_cache_key)).items()}

        missing = [k for k in unique if k not in series]
        if missing:
            batches = list(_chunks(missing, BATCH_SIZE))
            with ThreadPoolExecutor(max_workers=min(self._workers, len(batches))) as pool:
                results = pool.map(lambda b: self._fetch_batch(b, start_d, end_d), batches)
                for batch, result in zip(batches, results):
                    series.update(zip(batch, result))
            cache.set_many({cache_key(k): series[k] for k in missing}, CACHE_TTL_S)
        return [series[k] for k in keys]

    def _fetch_batch(self, cells: list[LatLng], start_d, end_d) -> list[HourlySeries]:
        body = self._http.get_json(
            self._url,
            {
                "latitude": ",".join(str(c[0]) for c in cells),
                "longitude": ",".join(str(c[1]) for c in cells),
                "hourly": "wind_speed_10m,rain,showers,snowfall",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "GMT",
                "start_date": start_d.isoformat(),
                "end_date": end_d.isoformat(),
            },
        )
        if isinstance(body, dict) and body.get("error"):
            raise UpstreamError(f"Weather provider: {body.get('reason', 'unknown error')}")
        payloads = body if isinstance(body, list) else [body]  # single location returns an object
        return [self._parse(p["hourly"]) for p in payloads]

    @staticmethod
    def _parse(hourly: dict) -> HourlySeries:
        zero = lambda xs: tuple(x or 0.0 for x in xs)  # noqa: E731  (nulls -> 0)
        rain, showers = zero(hourly["rain"]), zero(hourly["showers"])
        return HourlySeries(
            start=datetime.fromisoformat(hourly["time"][0]).replace(tzinfo=timezone.utc),
            wind_mph=zero(hourly["wind_speed_10m"]),
            rain_in=tuple(r + s for r, s in zip(rain, showers)),
            snow_in=zero(hourly["snowfall"]),
        )
