"""Floodsense API: rainfall-driven flood probability from Open-Meteo data."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from risk import predict_flood_probability
from weather import fetch_weather_data, fetch_weather_batch, fetch_weather_series, CACHE_TTL_SECONDS
from geocode import search_places

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
    hourly: list["HourlyPoint"] = []


class HealthResponse(BaseModel):
    status: str


class HourlyPoint(BaseModel):
    time: str
    precipitation: float


class GridCell(BaseModel):
    lat: float
    lon: float
    flood_probability: float | None = None
    risk_band: str | None = None
    rain_1h: float
    rain_6h: float
    rain_24h: float
    elevation_m: float = 0.0
    soil_moisture: float = 0.0
    stale: bool = False


class FloodGridResponse(BaseModel):
    north: float
    south: float
    east: float
    west: float
    res: int
    cells: list[GridCell]
    min_probability: float | None = None
    max_probability: float | None = None
    source: str
    fetch_timestamp: str | None = None
    stale: bool = False


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

    hourly: list[HourlyPoint] = []
    try:
        series = fetch_weather_series(lat, lon)
        hourly = [
            HourlyPoint(time=s["time"], precipitation=s["precipitation"])
            for s in series
        ]
    except Exception:
        pass

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
        hourly=hourly,
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


GRID_RES_MIN = 2
GRID_RES_MAX = 8


@app.get("/flood-grid", response_model=FloodGridResponse)
def flood_grid(
    north: float = Query(..., description="Northern latitude bound"),
    south: float = Query(..., description="Southern latitude bound"),
    east: float = Query(..., description="Eastern longitude bound"),
    west: float = Query(..., description="Western longitude bound"),
    res: int = Query(default=6, description="Grid resolution (2-8)"),
) -> FloodGridResponse:
    """Sample a flood-risk grid over the current map viewport bounds."""
    if north <= south or east <= west:
        raise HTTPException(status_code=400, detail="Invalid bounds: north must be > south and east must be > west")
    if res < GRID_RES_MIN:
        raise HTTPException(status_code=400, detail=f"res must be >= {GRID_RES_MIN}")
    if res > GRID_RES_MAX:
        res = GRID_RES_MAX

    # Generate res*res cell centres in row-major order (row = lat index, col = lon index).
    points: list[tuple[float, float]] = []
    lat_step = (north - south) / res
    lon_step = (east - west) / res
    for j in range(res):
        for i in range(res):
            lat = south + (j + 0.5) * lat_step
            lon = west + (i + 0.5) * lon_step
            points.append((lat, lon))

    # Fetch all weather in a single batch request.
    CHUNK = 60
    weather_results: list[dict | None] = []
    for start in range(0, len(points), CHUNK):
        chunk = points[start:start + CHUNK]
        weather_results.extend(fetch_weather_batch(chunk))

    cells: list[GridCell] = []
    probs: list[float] = []
    all_failed = True

    for idx, w in enumerate(weather_results):
        lat, lon = points[idx]
        if w is None:
            cells.append(GridCell(
                lat=lat, lon=lon,
                rain_1h=0.0, rain_6h=0.0, rain_24h=0.0,
                stale=True,
            ))
            continue

        all_failed = False
        prediction = predict_flood_probability(
            w["rain_1h"], w["rain_6h"], w["rain_24h"],
            w.get("elevation_m", 0.0), w.get("soil_moisture", 0.0),
        )
        prob = prediction["flood_probability"]
        probs.append(prob)
        cells.append(GridCell(
            lat=lat, lon=lon,
            flood_probability=prob,
            risk_band=prediction["risk_band"],
            rain_1h=w["rain_1h"], rain_6h=w["rain_6h"], rain_24h=w["rain_24h"],
            elevation_m=w.get("elevation_m", 0.0),
            soil_moisture=w.get("soil_moisture", 0.0),
            stale=w.get("stale", False),
        ))

    if all_failed:
        raise HTTPException(status_code=503, detail="All grid cells failed and no cache is available")

    fetch_ts = None
    grid_stale = False
    for w in weather_results:
        if w is not None:
            fetch_ts = w.get("fetch_timestamp", fetch_ts)
            if w.get("stale", False):
                grid_stale = True
            break

    min_prob = min(probs) if probs else None
    max_prob = max(probs) if probs else None

    return FloodGridResponse(
        north=north, south=south, east=east, west=west,
        res=res,
        cells=cells,
        min_probability=min_prob,
        max_probability=max_prob,
        source="open-meteo",
        fetch_timestamp=fetch_ts,
        stale=grid_stale,
    )


class GeocodeResult(BaseModel):
    name: str
    country: str | None = None
    admin1: str | None = None
    latitude: float
    longitude: float


class GeocodeResponse(BaseModel):
    results: list[GeocodeResult]


@app.get("/geocode", response_model=GeocodeResponse)
def geocode(
    q: str = Query(..., description="Search query"),
    count: int = Query(default=8, ge=1, le=10),
) -> GeocodeResponse:
    """Forward-geocode a place name via Open-Meteo geocoding."""
    results = search_places(q, count)
    return GeocodeResponse(
        results=[
            GeocodeResult(
                name=r["name"],
                country=r.get("country"),
                admin1=r.get("admin1"),
                latitude=r["latitude"],
                longitude=r["longitude"],
            )
            for r in results
        ]
    )