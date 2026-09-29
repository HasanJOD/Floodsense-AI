"""Tests for the Floodsense flood-probability API.

No live network calls: the weather provider is mocked.
"""

from __future__ import annotations

import time
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from main import app, MONITORED
from risk import predict_flood_probability
from weather import CACHE_TTL_SECONDS, _cache, fetch_weather_data

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_rf_high_rain_probability():
    p = predict_flood_probability(30, 40, 80)
    assert 0.0 <= p["flood_probability"] <= 100.0
    assert p["risk_band"] in ("HIGH", "SEVERE")
    assert p["method"] in ("random_forest", "heuristic_rules")
    assert set(p["class_probabilities"].keys()) == {"LOW", "MODERATE", "HIGH", "SEVERE"}


def test_probability_bounds_for_extremes():
    low = predict_flood_probability(0, 0, 0)
    assert low["flood_probability"] <= 25.0
    assert low["risk_band"] == "LOW"
    high = predict_flood_probability(60, 100, 200)
    assert high["flood_probability"] >= 50.0
    assert high["risk_band"] in ("HIGH", "SEVERE")


def test_response_shape():
    times = [f"2026-01-01T{h:02d}:00" for h in range(30)]
    raw = {"hourly": {"time": times, "precipitation": [1.0] * 30}}
    _cache.clear()
    with mock.patch("weather._fetch_raw", return_value=raw):
        r = client.get("/flood-probability", params={"lat": 13.04, "lon": 80.24})
    assert r.status_code == 200
    body = r.json()
    for key in (
        "flood_probability",
        "risk_band",
        "class_probabilities",
        "method",
        "model_limitations",
        "rain_1h",
        "rain_6h",
        "rain_24h",
        "elevation_m",
        "soil_moisture",
        "source",
        "stale",
    ):
        assert key in body, f"missing {key}"
    assert 0.0 <= body["flood_probability"] <= 100.0
    assert body["source"] == "open-meteo"


def test_weather_returns_trailing_totals_only():
    # Simulate 30 historical hours of precipitation (no future hours).
    times = [f"2026-01-01T{h:02d}:00" for h in range(30)]
    precip = [1.0] * 30
    raw = {"hourly": {"time": times, "precipitation": precip}}
    with mock.patch("weather._fetch_raw", return_value=raw):
        _cache.clear()
        data = fetch_weather_data(13.04, 80.24)
    assert data["rain_1h"] == 1.0
    assert data["rain_6h"] == 6.0
    assert data["rain_24h"] == 24.0
    assert data["stale"] is False
    assert data["source"] == "open-meteo"


def test_weather_does_not_sum_future_hours():
    # Provide 48 hours; totals must use the LAST 24, not the first.
    times = [f"2026-01-01T{h:02d}:00" for h in range(48)]
    precip = [100.0] * 24 + [1.0] * 24
    raw = {"hourly": {"time": times, "precipitation": precip}}
    with mock.patch("weather._fetch_raw", return_value=raw):
        _cache.clear()
        data = fetch_weather_data(13.04, 80.24)
    assert data["rain_1h"] == 1.0
    assert data["rain_6h"] == 6.0
    assert data["rain_24h"] == 24.0


def test_cache_serves_without_network():
    times = [f"2026-01-01T{h:02d}:00" for h in range(30)]
    precip = [2.0] * 30
    raw = {"hourly": {"time": times, "precipitation": precip}}
    _cache.clear()
    with mock.patch("weather._fetch_raw", return_value=raw) as mocked:
        first = fetch_weather_data(13.04, 80.24)
        second = fetch_weather_data(13.04, 80.24)
    assert mocked.call_count == 1
    assert first["rain_24h"] == second["rain_24h"] == 48.0
    assert second["stale"] is False


def test_stale_cache_on_failure():
    times = [f"2026-01-01T{h:02d}:00" for h in range(30)]
    precip = [3.0] * 30
    raw = {"hourly": {"time": times, "precipitation": precip}}
    _cache.clear()
    with mock.patch("weather._fetch_raw", return_value=raw):
        fetch_weather_data(13.04, 80.24)

    # Expire the cache entry so the next call must hit the network.
    key = next(iter(_cache))
    _cache[key].stored_at = time.time() - (CACHE_TTL_SECONDS + 60)

    with mock.patch("weather._fetch_raw", side_effect=RuntimeError("network down")):
        stale = fetch_weather_data(13.04, 80.24)
    assert stale["stale"] is True
    assert stale["rain_24h"] == 72.0


def test_no_cache_returns_error():
    _cache.clear()
    with mock.patch("weather._fetch_raw", side_effect=RuntimeError("network down")):
        r = client.get("/flood-probability", params={"lat": 13.04, "lon": 80.24})
    assert r.status_code == 503


def test_fallback_when_model_missing():
    with mock.patch("risk._load_model", return_value=None):
        p = predict_flood_probability(20, 30, 60)
    assert p["method"] == "heuristic_rules"
    assert 0.0 <= p["flood_probability"] <= 100.0


def test_location_name_optional():
    with mock.patch("weather._fetch_raw", side_effect=RuntimeError("down")):
        r = client.get(
            "/flood-probability",
            params={"lat": 13.04, "lon": 80.24, "location_name": "Chennai"},
        )
    assert r.status_code == 503
    # With a working (mocked) fetch, the name should pass through.
    times = [f"2026-01-01T{h:02d}:00" for h in range(30)]
    raw = {"hourly": {"time": times, "precipitation": [1.0] * 30}}
    _cache.clear()
    with mock.patch("weather._fetch_raw", return_value=raw):
        r = client.get(
            "/flood-probability",
            params={"lat": 13.04, "lon": 80.24, "location_name": "Chennai"},
        )
    assert r.status_code == 200
    assert r.json()["location_name"] == "Chennai"


def test_cache_ttl_constant():
    assert 300 <= CACHE_TTL_SECONDS <= 900


# --- Monitoring endpoints ---

def _clear_monitors():
    MONITORED.clear()


def test_monitor_add_and_list():
    _clear_monitors()
    r = client.post("/monitor", json={"name": "Chennai", "lat": 13.04, "lon": 80.24, "threshold": 40.0})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Chennai"
    assert body["threshold"] == 40.0
    assert body["last_probability"] is not None
    assert "alert" in body

    r2 = client.get("/monitor")
    assert r2.status_code == 200
    locs = r2.json()["locations"]
    assert len(locs) == 1
    assert locs[0]["name"] == "Chennai"


def test_monitor_delete():
    _clear_monitors()
    client.post("/monitor", json={"name": "Test", "lat": 13.04, "lon": 80.24})
    assert len(MONITORED) == 1
    mid = next(iter(MONITORED))
    r = client.delete(f"/monitor/{mid}")
    assert r.status_code == 200
    assert len(MONITORED) == 0
    r2 = client.delete(f"/monitor/{mid}")
    assert r2.status_code == 404


def test_monitor_alert_threshold():
    _clear_monitors()
    # High rain should trigger alert when threshold is low.
    times = [f"2026-01-01T{h:02d}:00" for h in range(30)]
    raw = {"hourly": {"time": times, "precipitation": [10.0] * 30}}
    _cache.clear()
    with mock.patch("weather._fetch_raw", return_value=raw):
        r = client.post(
            "/monitor",
            json={"name": "AlertTest", "lat": 13.04, "lon": 80.24, "threshold": 10.0},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["alert"] is True


def test_monitor_delete_missing():
    _clear_monitors()
    r = client.delete("/monitor/9999")
    assert r.status_code == 404


# --- Grid / batch / geocode / series extensions ---

from weather import BATCH_SIZE_LIMIT, fetch_weather_batch, fetch_weather_series
from geocode import search_places


def _mock_times(n=30):
    return [f"2026-01-01T{h:02d}:00" for h in range(n)]


def _mock_raw_for_batch(points):
    """Build a multi-coordinate raw response list matching *points*."""
    raw = []
    for _ in points:
        raw.append(
            {
                "hourly": {
                    "time": _mock_times(30),
                    "precipitation": [1.0] * 30,
                }
            }
        )
    return raw


def test_grid_shape():
    _cache.clear()
    raw = _mock_raw_for_batch([(13.04, 80.24)] * 36)
    with mock.patch("weather._fetch_raw_batch", return_value=raw), \
         mock.patch("weather._fetch_elevation", return_value=0.0):
        results = fetch_weather_batch([(13.04, 80.24)] * 36)
    assert len(results) == 36
    assert all(r is not None for r in results)
    assert results[0]["rain_24h"] == 24.0


def test_grid_batch_is_single_call():
    _cache.clear()
    raw = _mock_raw_for_batch([(13.04, 80.24)] * 36)
    with mock.patch("weather._fetch_raw_batch", return_value=raw) as mocked, \
         mock.patch("weather._fetch_elevation", return_value=0.0):
        fetch_weather_batch([(13.04, 80.24)] * 36)
    assert mocked.call_count == 1


def test_batch_normalises_single_and_multi():
    _cache.clear()

    # Single-point response returns a dict (not a list).
    single_raw = {"hourly": {"time": _mock_times(30), "precipitation": [2.0] * 30}}
    with mock.patch("weather._fetch_raw_batch", return_value=single_raw), \
         mock.patch("weather._fetch_elevation", return_value=0.0):
        results = fetch_weather_batch([(13.04, 80.24)])
    assert len(results) == 1
    assert results[0] is not None
    assert results[0]["rain_24h"] == 48.0

    # Multi-point response returns a list.
    _cache.clear()
    multi_raw = [
        {"hourly": {"time": _mock_times(30), "precipitation": [1.0] * 30}},
        {"hourly": {"time": _mock_times(30), "precipitation": [3.0] * 30}},
    ]
    with mock.patch("weather._fetch_raw_batch", return_value=multi_raw), \
         mock.patch("weather._fetch_elevation", return_value=0.0):
        results = fetch_weather_batch([(13.0, 80.0), (13.1, 80.1)])
    assert len(results) == 2
    assert results[0]["rain_24h"] == 24.0
    assert results[1]["rain_24h"] == 72.0


def test_batch_oversize_raises():
    with pytest.raises(ValueError):
        fetch_weather_batch([(0, 0)] * (BATCH_SIZE_LIMIT + 1))


def test_series_is_24_historical_hours():
    times = [f"2026-01-01T{h:02d}:00" for h in range(48)]
    precip = [10.0] * 24 + [1.0] * 24
    raw = {"hourly": {"time": times, "precipitation": precip}}
    _cache.clear()
    with mock.patch("weather._fetch_raw", return_value=raw), \
         mock.patch("weather._fetch_elevation", return_value=0.0):
        series = fetch_weather_series(13.04, 80.24)
    assert len(series) == 24
    # Only the trailing 24 entries (all 1.0) should appear, never the 10.0s.
    assert all(s["precipitation"] == 1.0 for s in series)


def test_geocode_maps_results():
    raw = {
        "results": [
            {"name": "Berlin", "country": "Germany", "admin1": "Berlin", "latitude": 52.52, "longitude": 13.405},
            {"name": "Berlin", "country": "United States", "admin1": "New Hampshire", "latitude": 42.87, "longitude": -71.85},
        ]
    }
    with mock.patch("geocode._fetch_geocode_raw", return_value=raw):
        results = search_places("Berlin")
    assert len(results) == 2
    assert results[0]["name"] == "Berlin, Germany"
    assert results[1]["name"] == "Berlin, New Hampshire"
    assert results[0]["latitude"] == 52.52


def test_geocode_empty_query_returns_empty_list():
    assert search_places("") == []


def _mock_weather_for_grid(res=6):
    """Build weather results for a grid of *res* x *res* cells."""
    return {
        "rain_1h": 1.0,
        "rain_6h": 6.0,
        "rain_24h": 24.0,
        "elevation_m": 10.0,
        "soil_moisture": 0.3,
        "source": "open-meteo",
        "fetch_timestamp": "2026-01-01T00:00:00Z",
        "stale": False,
    }


def test_grid_endpoint_shape():
    _cache.clear()
    n = 6 * 6
    batch_result = [_mock_weather_for_grid() for _ in range(n)]
    with mock.patch("main.fetch_weather_batch", return_value=batch_result):
        r = client.get("/flood-grid", params={
            "north": 14.0, "south": 12.0, "east": 81.0, "west": 79.0, "res": 6,
        })
    assert r.status_code == 200
    body = r.json()
    assert len(body["cells"]) == n
    for cell in body["cells"]:
        assert 12.0 < cell["lat"] < 14.0
        assert 79.0 < cell["lon"] < 81.0
    assert body["min_probability"] is not None
    assert body["max_probability"] is not None


def test_grid_res_clamped():
    _cache.clear()
    batch_result = [_mock_weather_for_grid() for _ in range(8 * 8)]
    def _fake_batch(points):
        return batch_result[:len(points)]
    with mock.patch("main.fetch_weather_batch", side_effect=_fake_batch):
        r = client.get("/flood-grid", params={
            "north": 14.0, "south": 12.0, "east": 81.0, "west": 79.0, "res": 99,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["res"] == 8
    assert len(body["cells"]) == 64

    _cache.clear()
    r2 = client.get("/flood-grid", params={
        "north": 14.0, "south": 12.0, "east": 81.0, "west": 79.0, "res": 1,
    })
    assert r2.status_code == 400


def test_grid_endpoint_single_call():
    _cache.clear()
    n = 6 * 6
    batch_result = [_mock_weather_for_grid() for _ in range(n)]
    with mock.patch("main.fetch_weather_batch", return_value=batch_result) as mocked:
        client.get("/flood-grid", params={
            "north": 14.0, "south": 12.0, "east": 81.0, "west": 79.0, "res": 6,
        })
    assert mocked.call_count == 1


def test_grid_inverted_bounds_400():
    r = client.get("/flood-grid", params={
        "north": 12.0, "south": 14.0, "east": 81.0, "west": 79.0, "res": 6,
    })
    assert r.status_code == 400


def test_flood_probability_includes_hourly():
    _cache.clear()
    times = [f"2026-01-01T{h:02d}:00" for h in range(30)]
    raw = {"hourly": {"time": times, "precipitation": [1.0] * 30}}
    with mock.patch("weather._fetch_raw", return_value=raw), \
         mock.patch("weather._fetch_elevation", return_value=0.0):
        r = client.get("/flood-probability", params={"lat": 13.04, "lon": 80.24})
    assert r.status_code == 200
    assert "hourly" in r.json()
    assert isinstance(r.json()["hourly"], list)