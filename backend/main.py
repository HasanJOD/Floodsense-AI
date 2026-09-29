"""Floodsense API: rainfall-driven flood probability from Open-Meteo data."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from risk import predict_flood_probability
from weather import fetch_weather_data

app = FastAPI(title="Floodsense")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory monitored locations list. Each entry:
#   {id, name, lat, lon, threshold, last_check, last_probability, alert}
MONITORED: dict[int, dict] = {}
_NEXT_ID = 1


class FloodProbabilityResponse(BaseModel):
    location_name: str | None = None
    latitude: float
    longitude: float
    flood_probability: float = Field(..., ge=0.0, le=100.0)
    risk_band: str
    class_probabilities: dict[str, float]
    method: str
    model_limitations: str
    rain_1h: float
    rain_6h: float
    rain_24h: float
    elevation_m: float = 0.0
    soil_moisture: float = 0.0
    source: str
    weather_timestamp: str | None = None
    fetch_timestamp: str | None = None
    stale: bool = False


class HealthResponse(BaseModel):
    status: str


class MonitoredLocation(BaseModel):
    name: str
    lat: float
    lon: float
    threshold: float = Field(default=50.0, ge=0.0, le=100.0)


class MonitoredStatus(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    threshold: float
    last_check: float | None = None
    last_probability: float | None = None
    last_band: str | None = None
    alert: bool = False
    stale: bool = False


class MonitoredListResponse(BaseModel):
    locations: list[MonitoredStatus]


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/flood-probability", response_model=FloodProbabilityResponse)
def flood_probability(
    lat: float = Query(..., description="Latitude in decimal degrees"),
    lon: float = Query(..., description="Longitude in decimal degrees"),
    location_name: str | None = Query(default=None, description="Optional human-readable location name"),
) -> FloodProbabilityResponse:
    try:
        weather = fetch_weather_data(lat, lon)
    except Exception as exc:  # network failure with no usable cache
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch weather data for location: {exc}",
        ) from exc

    rain_1h = weather["rain_1h"]
    rain_6h = weather["rain_6h"]
    rain_24h = weather["rain_24h"]
    elevation_m = weather.get("elevation_m", 0.0)
    soil_moisture = weather.get("soil_moisture", 0.0)

    prediction = predict_flood_probability(
        rain_1h, rain_6h, rain_24h, elevation_m, soil_moisture
    )

    return FloodProbabilityResponse(
        location_name=location_name,
        latitude=lat,
        longitude=lon,
        flood_probability=prediction["flood_probability"],
        risk_band=prediction["risk_band"],
        class_probabilities=prediction["class_probabilities"],
        method=prediction["method"],
        model_limitations=prediction["model_limitations"],
        rain_1h=rain_1h,
        rain_6h=rain_6h,
        rain_24h=rain_24h,
        elevation_m=elevation_m,
        soil_moisture=soil_moisture,
        source=weather["source"],
        weather_timestamp=weather.get("weather_timestamp"),
        fetch_timestamp=weather.get("fetch_timestamp"),
        stale=weather.get("stale", False),
    )


@app.post("/monitor", response_model=MonitoredStatus)
def add_monitor(loc: MonitoredLocation) -> MonitoredStatus:
    global _NEXT_ID
    mid = _NEXT_ID
    _NEXT_ID += 1
    MONITORED[mid] = {
        "id": mid,
        "name": loc.name,
        "lat": loc.lat,
        "lon": loc.lon,
        "threshold": loc.threshold,
        "last_check": None,
        "last_probability": None,
        "last_band": None,
        "alert": False,
    }
    return _refresh_one(mid)


@app.get("/monitor", response_model=MonitoredListResponse)
def list_monitor() -> MonitoredListResponse:
    return MonitoredListResponse(
        locations=[_refresh_one(mid) for mid in list(MONITORED.keys())]
    )


@app.delete("/monitor/{monitor_id}")
def delete_monitor(monitor_id: int):
    if monitor_id not in MONITORED:
        raise HTTPException(status_code=404, detail="monitor not found")
    del MONITORED[monitor_id]
    return {"status": "ok"}


def _refresh_one(monitor_id: int) -> MonitoredStatus:
    entry = MONITORED.get(monitor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="monitor not found")
    try:
        weather = fetch_weather_data(entry["lat"], entry["lon"])
    except Exception:
        if entry.get("last_check") is not None:
            return MonitoredStatus(
                id=entry["id"],
                name=entry["name"],
                lat=entry["lat"],
                lon=entry["lon"],
                threshold=entry["threshold"],
                last_check=entry["last_check"],
                last_probability=entry["last_probability"],
                last_band=entry["last_band"],
                alert=entry.get("alert", False),
                stale=True,
            )
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch weather for {entry['name']}",
        )
    prediction = predict_flood_probability(
        weather["rain_1h"],
        weather["rain_6h"],
        weather["rain_24h"],
        weather.get("elevation_m", 0.0),
        weather.get("soil_moisture", 0.0),
    )
    now = time.time()
    prob = prediction["flood_probability"]
    band = prediction["risk_band"]
    alert = prob >= entry["threshold"]
    entry.update({
        "last_check": now,
        "last_probability": prob,
        "last_band": band,
        "alert": alert,
    })
    return MonitoredStatus(
        id=entry["id"],
        name=entry["name"],
        lat=entry["lat"],
        lon=entry["lon"],
        threshold=entry["threshold"],
        last_check=now,
        last_probability=prob,
        last_band=band,
        alert=alert,
        stale=weather.get("stale", False),
    )