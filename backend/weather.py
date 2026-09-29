"""Open-Meteo weather fetching for Floodsense.

Fetches trailing (past) hourly precipitation for a given lat/lon and computes
accumulations over the last 1, 6 and 24 hours. Also fetches elevation and
current soil moisture, which are used as additional flood features.
Totals are always computed from historical hours only -- never from future
forecast hours.

A small per-location in-memory cache avoids calling Open-Meteo on every page
refresh. If a live fetch fails and a cached value exists, it is returned with
``stale=True`` so the UI can warn the user.
"""

from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass

import httpx

# Cache TTL in seconds (10 minutes).
CACHE_TTL_SECONDS = 600
# Open-Meteo archive endpoint (free, no API key).
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class _CacheEntry:
    payload: dict
    stored_at: float


# Keyed by (lat_rounded, lon_rounded) so nearby locations share a cache entry.
_cache: dict[tuple[float, float], _CacheEntry] = {}


def _cache_key(lat: float, lon: float) -> tuple[float, float]:
    return (round(lat, 4), round(lon, 4))


def _iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _fetch_raw(lat: float, lon: float) -> dict:
    """Fetch hourly precipitation, elevation and soil moisture from Open-Meteo.

    All returned data is historical only -- no future forecast hours are used.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,soil_moisture",
        "past_days": 2,
        "forecast_days": 0,
        "timezone": "UTC",
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        return response.json()


def _fetch_elevation(lat: float, lon: float) -> float:
    """Fetch elevation (metres above sea level) for a location."""
    params = {
        "latitude": lat,
        "longitude": lon,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://api.open-meteo.com/v1/elevation",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
        elevations = data.get("elevation")
        if elevations and len(elevations) > 0:
            return float(elevations[0])
    except Exception:
        pass
    return 0.0


def _build_payload(lat: float, lon: float, raw: dict) -> dict:
    hourly = raw.get("hourly") or {}
    times = hourly.get("time") or []
    precip = hourly.get("precipitation") or []
    soil = hourly.get("soil_moisture") or []

    if not times or not precip:
        raise ValueError("Open-Meteo returned no hourly precipitation data")

    # Take the trailing window from the most recent available hour backwards.
    # All values are historical; no future forecast hours are summed.
    precip = [float(p or 0.0) for p in precip]
    rain_1h = precip[-1]
    rain_6h = sum(precip[-6:])
    rain_24h = sum(precip[-24:])

    # Soil moisture: use the most recent value (m^3/m^3, 0-1 scale).
    soil_values = [float(s or 0.0) for s in soil]
    soil_moisture = soil_values[-1] if soil_values else 0.0

    elevation = _fetch_elevation(lat, lon)

    weather_timestamp = times[-1]
    return {
        "rain_1h": round(rain_1h, 2),
        "rain_6h": round(rain_6h, 2),
        "rain_24h": round(rain_24h, 2),
        "elevation_m": round(elevation, 1),
        "soil_moisture": round(soil_moisture, 4),
        "source": "open-meteo",
        "weather_timestamp": weather_timestamp,
        "fetch_timestamp": _iso_now(),
        "stale": False,
    }


def fetch_weather_data(lat: float, lon: float) -> dict:
    """Return trailing rainfall + elevation + soil moisture for a location.

    Uses a short-lived cache. Raises if no live data can be fetched and no
    cached value is available.
    """
    key = _cache_key(lat, lon)
    now = time.time()

    # Serve fresh cache without hitting the network.
    cached = _cache.get(key)
    if cached is not None and (now - cached.stored_at) < CACHE_TTL_SECONDS:
        fresh = dict(cached.payload)
        fresh["stale"] = False
        return fresh

    try:
        raw = _fetch_raw(lat, lon)
        payload = _build_payload(lat, lon, raw)
    except Exception:
        # Fall back to any cached value, even if expired, and flag it stale.
        if cached is not None:
            stale = dict(cached.payload)
            stale["stale"] = True
            return stale
        raise

    _cache[key] = _CacheEntry(payload=payload, stored_at=now)
    return payload