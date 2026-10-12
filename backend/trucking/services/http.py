"""One hardened HTTP client shared by all third-party integrations."""
from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..errors import UpstreamError


class Http:
    def __init__(self, timeout: float, user_agent: str = "spotter-weather-routing/1.0"):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers["User-Agent"] = user_agent
        retry = Retry(total=2, backoff_factor=0.4, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
        self._session.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=16))
        self._session.mount("http://", HTTPAdapter(max_retries=retry, pool_maxsize=16))

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """Return the parsed body for any non-5xx response so callers can read provider error codes."""
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            if response.status_code >= 500:
                raise UpstreamError(f"{requests.utils.urlparse(url).netloc} returned {response.status_code}")
            return response.json()
        except requests.RequestException as exc:
            raise UpstreamError(f"Could not reach {requests.utils.urlparse(url).netloc}") from exc
        except ValueError as exc:
            raise UpstreamError("Provider returned an invalid response") from exc
