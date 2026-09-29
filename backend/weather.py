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
from typing import Any

import httpx

# Cache TTL in seconds (10 minutes).
CACHE_TTL_SECONDS = 600
# Open-Meteo forecast endpoint (free, no API key).
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"

# Open-Meteo rejects the bare ``soil_moisture`` param; the shallow-surface
# variable is named ``soil_moisture_0_to_1cm``. We request that and map it back
# to the ``soil_moisture`` field the model expects.
SOIL_MOISTURE_PARAM = "soil_moisture_0_to_1cm"
BATCH_SIZE_LIMIT = 60


@dataclass
class _CacheEntry:
    payload: dict
    series: list[dict]
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
        "hourly": f"precipitation,{SOIL_MOISTURE_PARAM}",
        "past_days": 2,
        "forecast_days": 0,
        "timezone": "UTC",
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        return response.json()


def _fetch_raw_batch(points: list[tuple[float, float]]) -> dict | list:
    """Fetch weather for multiple coordinates in a single request.

    Open-Meteo returns a list when >1 coordinate, a dict when exactly 1.
    """
    lats = ",".join(str(p[0]) for p in points)
    lons = ",".join(str(p[1]) for p in points)
    params = {
        "latitude": lats,
        "longitude": lons,
        "hourly": f"precipitation,{SOIL_MOISTURE_PARAM}",
        "past_days": 2,
        "forecast_days": 0,
        "timezone": "UTC",
    }
    with httpx.Client(timeout=15.0) as client:
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
                OPEN_METEO_ELEVATION_URL,
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


def _extract_hourly(raw: dict | list, index: int) -> dict | None:
    """Extract the per-hourly arrays for the cell at *index* from a raw response.

    Handles both single-coordinate (dict) and multi-coordinate (list) responses.
    Returns ``None`` if the entry is malformed.
    """
    if isinstance(raw, list):
        if index >= len(raw):
            return None
        entry = raw[index]
    else:
        entry = raw
    if not isinstance(entry, dict):
        return None
    hourly = entry.get("hourly")
    if not isinstance(hourly, dict):
        return None
    times = hourly.get("time")
    precip = hourly.get("precipitation")
    soil = hourly.get(SOIL_MOISTURE_PARAM)
    if not times or not precip:
        return None
    return {"times": times, "precip": precip, "soil": soil}


def _hourly_to_payload(
    hours: dict[str, Any],
    lat: float,
    lon: float,
    include_series: bool = False,
) -> dict:
    """Convert extracted hourly arrays into a weather payload dict.

    Shared by single-point, batch and series code paths so that the
    ``rain_1h / rain_6h / rain_24h`` computation is never duplicated.
    """
    times = hours["times"]
    precip = [float(p or 0.0) for p in hours["precip"]]
    soil = hours["soil"] or []
    soil_values = [float(s or 0.0) for s in soil]

    rain_1h = precip[-1]
    rain_6h = sum(precip[-6:])
    rain_24h = sum(precip[-24:])
    soil_moisture = soil_values[-1] if soil_values else 0.0

    elevation = _fetch_elevation(lat, lon)
    weather_timestamp = times[-1]

    payload: dict[str, Any] = {
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

    if include_series:
        n = len(times)
        series = []
        for i in range(max(0, n - 24), n):
            series.append({"time": times[i], "precipitation": precip[i]})
        payload["hourly"] = series

    return payload


def _build_payload(lat: float, lon: float, raw: dict) -> dict:
    """Build a single-point weather payload from a raw Open-Meteo response dict."""
    hours = _extract_hourly(raw, 0)
    if hours is None:
        raise ValueError("Open-Meteo returned no hourly precipitation data")
    return _hourly_to_payload(hours, lat, lon)


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
        hours = _extract_hourly(raw, 0)
        if hours is None:
            raise ValueError("Open-Meteo returned no hourly precipitation data")
        payload = _hourly_to_payload(hours, lat, lon)
        series = _hourly_to_payload(hours, lat, lon, include_series=True)
        _cache[key] = _CacheEntry(
            payload=payload, series=series.get("hourly", []), stored_at=now
        )
        return payload
    except Exception:
        # Fall back to any cached value, even if expired, and flag it stale.
        if cached is not None:
            stale = dict(cached.payload)
            stale["stale"] = True
            return stale
        raise


def fetch_weather_batch(
    points: list[tuple[float, float]],
) -> list[dict | None]:
    """Fetch weather for multiple locations in a single batch request.

    Returns one entry per input point, in order; ``None`` for any point that
    came back malformed. Length always equals the input length so the grid can
    zip by index.

    Reuses the existing per-location cache: cached points are served without a
    network call and only the uncached subset is requested. Expired cache
    entries that fall back to stale data are flagged with ``stale=True``.

    The batch is capped at ``BATCH_SIZE_LIMIT`` points; callers must split
    larger lists into chunks.
    """
    if len(points) > BATCH_SIZE_LIMIT:
        raise ValueError(
            f"fetch_weather_batch received {len(points)} points; "
            f"maximum is {BATCH_SIZE_LIMIT}. Split into chunks."
        )

    results: list[dict | None] = [None] * len(points)
    uncached_indices: list[int] = []
    uncached_points: list[tuple[float, float]] = []

    now = time.time()
    for i, (lat, lon) in enumerate(points):
        key = _cache_key(lat, lon)
        cached = _cache.get(key)
        if cached is not None and (now - cached.stored_at) < CACHE_TTL_SECONDS:
            fresh = dict(cached.payload)
            fresh["stale"] = False
            results[i] = fresh
        else:
            uncached_indices.append(i)
            uncached_points.append((lat, lon))

    if uncached_points:
        raw = _fetch_raw_batch(uncached_points)
        normalised = raw if isinstance(raw, list) else [raw]
        for j, i in enumerate(uncached_indices):
            lat, lon = uncached_points[j]
            key = _cache_key(lat, lon)
            hours = _extract_hourly(normalised, j)
            if hours is not None:
                payload = _hourly_to_payload(hours, lat, lon)
                _cache[key] = _CacheEntry(
                    payload=payload, series=[], stored_at=now
                )
                results[i] = payload
            else:
                cached = _cache.get(key)
                if cached is not None:
                    stale = dict(cached.payload)
                    stale["stale"] = True
                    results[i] = stale
                # else: results[i] stays None

    return results


def fetch_weather_series(lat: float, lon: float) -> list[dict]:
    """Return trailing 24h precipitation per hour for a location (for charts).

    Historical only, consistent with the ``test_weather_does_not_sum_future_hours``
    guarantee. Uses the cache. On total failure, returns the cached series (if
    any) with each entry carrying ``stale=True``.
    """
    key = _cache_key(lat, lon)
    now = time.time()

    cached = _cache.get(key)
    if cached is not None and (now - cached.stored_at) < CACHE_TTL_SECONDS:
        return list(cached.series)

    try:
        raw = _fetch_raw(lat, lon)
        hours = _extract_hourly(raw, 0)
        if hours is None:
            raise ValueError("malformed response")
        payload = _hourly_to_payload(hours, lat, lon)
        series = _hourly_to_payload(hours, lat, lon, include_series=True)
        _cache[key] = _CacheEntry(
            payload=payload, series=series["hourly"], stored_at=now
        )
        return list(series["hourly"])
    except Exception:
        if cached is not None:
            return [
                {**entry, "stale": True} for entry in cached.series
            ]
        raise
