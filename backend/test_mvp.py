"""Tests for the Floodsense flood-probability API.

No live network calls: the weather provider is mocked.
"""

from __future__ import annotations

import time
from unittest import mock

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