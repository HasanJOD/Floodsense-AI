"""Open-Meteo geocoding for Floodsense.

Provides a cached, tolerant forward-geocoding wrapper around the Open-Meteo
geocoding API. Non-2xx or empty results return an empty list rather than
raising, so the UI degrades gracefully.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
CACHE_TTL_SECONDS = 600
MAX_RESULTS = 8

_geocode_cache: dict[tuple[str, int], tuple[float, list[dict]]] = {}


@dataclass
class _GeocodeCacheEntry:
    stored_at: float
    results: list[dict]


def _fetch_geocode_raw(q: str, count: int) -> dict:
    """Call the Open-Meteo geocoding API (mock target for tests)."""
    params = {
        "name": q,
        "count": count,
        "language": "en",
        "format": "json",
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.get(GEOCODE_URL, params=params)
        response.raise_for_status()
        return response.json()


def search_places(q: str, count: int = MAX_RESULTS) -> list[dict]:
    """Search for places matching *q*.

    Returns a list of dicts with keys: ``name``, ``country``, ``admin1``,
    ``latitude``, ``longitude``. The ``name`` field combines the city name
    with admin1/country when available so results are distinguishable
    ("Berlin, Germany" vs "Berlin, New Hampshire").

    Empty query or non-2xx response returns ``[]``.
    """
    if not q or not q.strip():
        return []
    count = max(1, min(count, 10))

    key = (q.strip(), count)
    now = time.time()
    cached = _geocode_cache.get(key)
    if cached is not None and (now - cached.stored_at) < CACHE_TTL_SECONDS:
        return list(cached.results)

    try:
        raw = _fetch_geocode_raw(q, count)
    except Exception:
        if cached is not None:
            return list(cached.results)
        return []

    results: list[dict] = []
    for item in raw.get("results", []):
        name = item.get("name", "")
        country = item.get("country")
        admin1 = item.get("admin1")
        parts = [name]
        if admin1 and admin1 != name:
            parts.append(admin1)
        elif country and country != name:
            parts.append(country)
        display_name = ", ".join(p for p in parts if p)
        results.append(
            {
                "name": display_name,
                "country": country,
                "admin1": admin1,
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
            }
        )

    _geocode_cache[key] = _GeocodeCacheEntry(
        stored_at=now, results=results
    )
    return results
