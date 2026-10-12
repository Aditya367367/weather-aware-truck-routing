"""Composition root: the only place concrete providers are wired together."""
from functools import lru_cache

from django.conf import settings

from .analysis import TripAnalyzer
from .geocoding import PhotonGeocoder
from .http import Http
from .routing import OsrmRouting
from .weather import OpenMeteoWeather


@lru_cache(maxsize=1)
def _http() -> Http:
    return Http(timeout=settings.HTTP_TIMEOUT_S)


@lru_cache(maxsize=1)
def get_analyzer() -> TripAnalyzer:
    router = OsrmRouting(_http(), settings.OSRM_BASE_URL, settings.TRUCK_TIME_FACTOR)
    return TripAnalyzer(router, OpenMeteoWeather(_http(), settings.OPEN_METEO_URL))


@lru_cache(maxsize=1)
def get_geocoder() -> PhotonGeocoder:
    return PhotonGeocoder(_http(), settings.PHOTON_URL)
