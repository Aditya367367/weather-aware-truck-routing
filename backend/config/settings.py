"""Settings. Stateless service: no database, everything tunable via env vars."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


DEBUG = env("DEBUG", "0") == "1"
SECRET_KEY = env("SECRET_KEY", "dev-only-insecure-key" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set when DEBUG=0")
ALLOWED_HOSTS = [h for h in env("ALLOWED_HOSTS", "*").split(",") if h]

INSTALLED_APPS = ["django.contrib.staticfiles", "rest_framework", "trucking"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES: dict = {}
USE_TZ = True
TIME_ZONE = "UTC"
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Serve the built React app from the same origin (single deployable).
_frontend = BASE_DIR / "frontend_dist"
if _frontend.exists():
    WHITENOISE_ROOT = _frontend
    WHITENOISE_INDEX_FILE = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_PERMISSION_CLASSES": [],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_RATES": {"anon": env("THROTTLE_RATE", "60/min")},
}

if env("REDIS_URL"):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": env("REDIS_URL")}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- Domain / integration config -------------------------------------------
OSRM_BASE_URL = env("OSRM_BASE_URL", "https://router.project-osrm.org")
OPEN_METEO_URL = env("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
PHOTON_URL = env("PHOTON_URL", "https://photon.komoot.io/api/")
HTTP_TIMEOUT_S = float(env("HTTP_TIMEOUT_S", "15"))
# OSRM only has a car profile; trucks are slower (governed speed, grades, hours of service).
TRUCK_TIME_FACTOR = float(env("TRUCK_TIME_FACTOR", "1.15"))
