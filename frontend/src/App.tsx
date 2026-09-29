import { useEffect, useState, useCallback, useMemo } from 'react';
import { useFloodProbability } from './hooks/useFloodProbability';
import { useFloodGrid } from './hooks/useFloodGrid';
import { useMonitors } from './hooks/useMonitors';
import { useGeolocation } from './hooks/useGeolocation';
import FloodMap from './components/FloodMap';
import RiskGauge from './components/RiskGauge';
import StatTile from './components/StatTile';
import ClassBreakdown from './components/ClassBreakdown';
import RainChart from './components/RainChart';
import MonitorList from './components/MonitorList';
import MonitorForm from './components/MonitorForm';
import MethodologyNote from './components/MethodologyNote';
import LocationSearch from './components/LocationSearch';
import RiskLegend from './components/RiskLegend';
import type { MapBounds } from './types';

const DEFAULT_LAT = 28.6139;
const DEFAULT_LON = 77.209;
const DEFAULT_LOCATION_NAME = 'Delhi, India';
const DEFAULT_ZOOM = 11;

const LOW_SYMBOL = '🌡';
const ELEV_SYMBOL = '⛰';
const SOIL_SYMBOL = '🌱';

export default function App() {
  const [lat, setLat] = useState(DEFAULT_LAT);
  const [lon, setLon] = useState(DEFAULT_LON);
  const [locationName, setLocationName] = useState<string | undefined>(DEFAULT_LOCATION_NAME);
  const [selectedPoint, setSelectedPoint] = useState<[number, number] | null>(null);

  const { data, loading, error, refresh } = useFloodProbability(lat, lon, locationName);
  const {
    monitors,
    add: addMonitor,
    remove: removeMonitor,
    loading: monitorsLoading,
    error: monitorError,
    mutateError: monitorMutateError,
  } = useMonitors();
  const { data: grid, requestGrid } = useFloodGrid();
  const geo = useGeolocation();

  // Track map center for grid requests and bounds.
  const mapCenter = [lat, lon] as [number, number];

  // When geolocation resolves, update the center.
  useEffect(() => {
    if (geo.coords) {
      setLat(geo.coords.lat);
      setLon(geo.coords.lon);
      setLocationName(undefined);
      setSelectedPoint([geo.coords.lat, geo.coords.lon]);
    }
  }, [geo.coords]);

  // Compute grid bounds from map center (world-view fallback if no data).
  const bounds: MapBounds = useMemo(
    () => ({
      north: lat + 0.5,
      south: lat - 0.5,
      east: lon + 0.5,
      west: lon - 0.5,
    }),
    [lat, lon],
  );

  // Request grid on lat/lon change (debounced inside the hook).
  useEffect(() => {
    requestGrid(bounds);
  }, [bounds, requestGrid]);

  const handleLocationSelect = useCallback((newLat: number, newLon: number, name?: string) => {
    setLat(newLat);
    setLon(newLon);
    setLocationName(name);
    setSelectedPoint([newLat, newLon]);
  }, []);

  const handleMapMove = useCallback((cLat: number, cLon: number) => {
    setLat((prev) => (Math.abs(prev - cLat) < 1e-6 ? prev : cLat));
    setLon((prev) => (Math.abs(prev - cLon) < 1e-6 ? prev : cLon));
    setLocationName(undefined);
  }, []);

  const handleMapClick = useCallback((cLat: number, cLon: number) => {
    setLat(cLat);
    setLon(cLon);
    setLocationName(undefined);
    setSelectedPoint([cLat, cLon]);
  }, []);

  const maxRiskValue = grid?.max_probability ?? null;

  return (
    <div className="flex h-screen overflow-hidden bg-flood-bg text-flood-text">
      <aside className="w-[380px] shrink-0 overflow-y-auto border-r border-flood-border bg-flood-panel">
        <div className="p-6">
          <header className="mb-6">
            <h1 className="text-3xl font-bold text-flood-text">Floodsense</h1>
            <p className="text-sm text-flood-muted">
              Live flood-probability monitoring powered by Open-Meteo
            </p>
          </header>

          <LocationSearch
            onLocationSelect={handleLocationSelect}
            currentLat={lat}
            currentLon={lon}
          />

          <div className="mb-4 flex gap-2">
            <button
              type="button"
              onClick={() => geo.request()}
              disabled={geo.loading}
              className="rounded-md border border-flood-border bg-flood-panel-2 px-3 py-2 text-sm font-medium text-flood-accent hover:bg-flood-bg disabled:cursor-not-allowed disabled:opacity-50"
            >
              {geo.loading ? 'Locating...' : 'Use My Location'}
            </button>
            <button
              type="button"
              onClick={refresh}
              disabled={loading}
              className="rounded-md border border-flood-border bg-flood-panel-2 px-3 py-2 text-sm font-medium text-flood-accent hover:bg-flood-bg disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          {geo.error && (
            <p className="mb-2 text-xs text-amber-400">{geo.error}</p>
          )}

          {loading && !data && (
            <p className="py-8 text-center text-flood-muted" aria-live="polite">
              Loading flood probability...
            </p>
          )}

          {error && !data && (
            <div className="mb-4 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {data && (
            <>
              <RiskGauge data={data} />

              <div className="mt-4 grid grid-cols-2 gap-3">
                <StatTile
                  label="Rain 1h"
                  value={`${data.rain_1h.toFixed(1)} mm`}
                  icon={<span aria-hidden="true">{LOW_SYMBOL}</span>}
                />
                <StatTile
                  label="Rain 6h"
                  value={`${data.rain_6h.toFixed(1)} mm`}
                  icon={<span aria-hidden="true">{LOW_SYMBOL}</span>}
                />
                <StatTile
                  label="Rain 24h"
                  value={`${data.rain_24h.toFixed(1)} mm`}
                  icon={<span aria-hidden="true">{LOW_SYMBOL}</span>}
                />
                <StatTile
                  label="Elevation"
                  value={`${data.elevation_m.toFixed(0)} m`}
                  icon={<span aria-hidden="true">{ELEV_SYMBOL}</span>}
                />
                <StatTile
                  label="Soil Moisture"
                  value={data.soil_moisture.toFixed(3)}
                  icon={<span aria-hidden="true">{SOIL_SYMBOL}</span>}
                />
                <StatTile
                  label="Max In View"
                  value={
                    maxRiskValue !== null
                      ? `${maxRiskValue.toFixed(0)}%`
                      : '--'
                  }
                />
              </div>

              <div className="mt-4">
                <ClassBreakdown data={data} />
              </div>

              <div className="mt-4">
                <RainChart hourly={data.hourly} loading={loading} />
              </div>

              <div className="mt-4">
                <MethodologyNote
                  data={{
                    method: data.method,
                    model_limitations: data.model_limitations,
                  }}
                />
              </div>
            </>
          )}

          <div className="mt-6">
            <h2 className="mb-3 text-xl font-semibold text-flood-text">
              Monitored Locations
            </h2>
            {monitorError && (
              <p className="mb-2 text-sm text-red-300">{monitorError}</p>
            )}
            <MonitorList
              monitors={monitors}
              onRemove={removeMonitor}
              loading={monitorsLoading}
            />
            <div className="mt-3">
              <MonitorForm
                onAdd={addMonitor}
                error={monitorMutateError}
              />
            </div>
          </div>

          <footer className="mt-6 border-t border-flood-border pt-4 text-xs text-flood-muted">
            <p className="font-medium text-amber-400">⚠ Disclaimer</p>
            <p className="mt-1">
              Floodsense is an early-warning information tool only. Its flood
              probability estimates come from a model trained on synthetic
              rainfall data combined with publicly available weather readings. It
              is NOT a substitute for official flood warnings, emergency services,
              or real-time monitoring. Always follow guidance from your local
              emergency management authority and evacuate immediately if advised.
            </p>
            <p className="mt-2">
              Data is ephemeral — monitored locations are stored in memory and
              will be lost on backend restart.
            </p>
          </footer>
        </div>
      </aside>

      <main className="relative flex-1">
        <FloodMap
          center={mapCenter}
          zoom={DEFAULT_ZOOM}
          onSelectPoint={handleMapClick}
          onMove={handleMapMove}
          selectedPoint={selectedPoint}
          grid={grid}
          monitors={monitors}
        />
        <RiskLegend />
      </main>
    </div>
  );
}
