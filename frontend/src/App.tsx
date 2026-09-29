import { useEffect, useState, useCallback } from 'react'
import {
  fetchFloodProbability,
  listMonitored,
  addMonitor,
  deleteMonitor,
} from './api'
import type {
  FloodProbabilityResponse,
  MonitoredLocation,
  MonitoredLocationInput,
  RiskBand,
} from './types'

const DEFAULT_LAT = 13.04
const DEFAULT_LON = 80.24
const POLL_INTERVAL = 600_000 // 10 minutes

const RISK_BADGE_CLASS: Record<RiskBand, string> = {
  LOW: 'badge-low',
  MODERATE: 'badge-moderate',
  HIGH: 'badge-high',
  SEVERE: 'badge-severe',
}

function RainCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-flood-border bg-flood-panel-2 p-4 text-center">
      <p className="text-xs uppercase text-flood-muted">Rain {label}</p>
      <p className="text-2xl font-bold text-flood-text">{value.toFixed(1)} mm</p>
    </div>
  )
}

function RiskBadge({ band }: { band: RiskBand }) {
  const cls = RISK_BADGE_CLASS[band] ?? 'badge-low'
  return (
    <span
      className={`rounded-full px-5 py-2 text-xl font-bold ${cls}`}
      aria-label={`Risk level: ${band}`}
    >
      {band}
    </span>
  )
}

function formatTime(ts: string | null): string {
  if (!ts) return '--'
  return new Date(ts).toLocaleString()
}

function classProbBar(
  label: RiskBand,
  value: number,
  max: number,
) {
  const pct = max > 0 ? (value / max) * 100 : 0
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs">
        <span className="text-flood-muted">{label}</span>
        <span className="text-flood-text">{value.toFixed(1)}%</span>
      </div>
      <div className="mt-1 h-2 w-full rounded bg-flood-bg">
        <div
          className="h-2 rounded"
          style={{
            width: `${pct}%`,
            backgroundColor: `var(--color-risk-${label.toLowerCase()})`,
          }}
        />
      </div>
    </div>
  )
}

export default function App() {
  const [lat, setLat] = useState(DEFAULT_LAT)
  const [lon, setLon] = useState(DEFAULT_LON)

  const [data, setData] = useState<FloodProbabilityResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [monitors, setMonitors] = useState<MonitoredLocation[]>([])
  const [monitorsLoading, setMonitorsLoading] = useState(false)
  const [monitorError, setMonitorError] = useState<string | null>(null)
  const [addName, setAddName] = useState('')
  const [addLat, setAddLat] = useState('')
  const [addLon, setAddLon] = useState('')
  const [addThreshold, setAddThreshold] = useState('50')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchFloodProbability(lat, lon)
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [lat, lon])

  const fetchMonitors = useCallback(async () => {
    setMonitorsLoading(true)
    setMonitorError(null)
    try {
      const result = await listMonitored()
      setMonitors(result)
    } catch (err) {
      setMonitorError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setMonitorsLoading(false)
    }
  }, [])

  const handleAddMonitor = async () => {
    const parsed = {
      name: addName,
      lat: parseFloat(addLat),
      lon: parseFloat(addLon),
      threshold: parseFloat(addThreshold),
    } satisfies MonitoredLocationInput
    try {
      const monitor = await addMonitor(parsed)
      setMonitors([...monitors, monitor])
      setAddName('')
      setAddLat('')
      setAddLon('')
      setAddThreshold('50')
    } catch (err) {
      setMonitorError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  const handleDeleteMonitor = async (id: number) => {
    try {
      await deleteMonitor(id)
      setMonitors(monitors.filter((m) => m.id !== id))
    } catch (err) {
      setMonitorError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  const handleGeolocate = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude)
        setLon(pos.coords.longitude)
      },
      (err) => {
        setError(`Geolocation error: ${err.message}`)
      },
    )
  }

  useEffect(() => {
    void fetchData()
    void fetchMonitors()
    const interval = setInterval(() => {
      void fetchData()
      void fetchMonitors()
    }, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchData, fetchMonitors])

  return (
    <div className="min-h-screen bg-flood-bg text-flood-text">
      <div className="mx-auto max-w-6xl p-6">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-flood-text">Floodsense</h1>
          <p className="text-flood-muted">
            Flood probability monitoring powered by Open-Meteo
          </p>
        </header>

        <section
          className="mb-8"
          aria-label="Location controls"
        >
          <h2 className="mb-4 text-xl font-semibold text-flood-text">Location</h2>
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label
                htmlFor="lat"
                className="block text-sm text-flood-muted"
              >
                Latitude
              </label>
              <input
                id="lat"
                type="number"
                step="0.0001"
                value={lat}
                onChange={(e) => setLat(parseFloat(e.target.value))}
                aria-label="Latitude"
                className="w-36 rounded-md border border-flood-border bg-flood-panel-2 px-3 py-2 text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
              />
            </div>
            <div>
              <label
                htmlFor="lon"
                className="block text-sm text-flood-muted"
              >
                Longitude
              </label>
              <input
                id="lon"
                type="number"
                step="0.0001"
                value={lon}
                onChange={(e) => setLon(parseFloat(e.target.value))}
                aria-label="Longitude"
                className="w-36 rounded-md border border-flood-border bg-flood-panel-2 px-3 py-2 text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
              />
            </div>
            <button
              type="button"
              onClick={handleGeolocate}
              className="rounded-md border border-flood-border bg-flood-panel px-4 py-2 font-medium text-flood-accent hover:bg-flood-panel-2"
            >
              Use My Location
            </button>
            <button
              type="button"
              onClick={() => void fetchData()}
              disabled={loading}
              className="rounded-md border border-flood-border bg-flood-panel px-4 py-2 font-medium text-flood-accent hover:bg-flood-panel-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </section>

        {!data && !error && (
          <div
            className="py-12 text-center text-flood-muted"
            aria-live="polite"
          >
            Loading flood probability...
          </div>
        )}

        {error && !data && loading === false && (
          <div className="mb-8 rounded-md border border-red-500/40 bg-red-500/10 p-4 text-red-300">
            {error}
          </div>
        )}

        {data && (
          <section
            className="mb-8"
            aria-label="Flood probability result"
          >
            <div className="rounded-lg border border-flood-border bg-flood-panel p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm uppercase text-flood-muted">
                    Flood Probability
                  </p>
                  <div className="text-6xl font-bold text-flood-text">
                    {data.flood_probability.toFixed(1)}%
                  </div>
                  {data.location_name && (
                    <p className="mt-1 text-sm text-flood-muted">
                      {data.location_name}
                    </p>
                  )}
                </div>
                <RiskBadge band={data.risk_band} />
              </div>

              <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <RainCard label="1h" value={data.rain_1h} />
                <RainCard label="6h" value={data.rain_6h} />
                <RainCard label="24h" value={data.rain_24h} />
              </div>

              <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <p className="mb-2 text-sm font-medium text-flood-text">
                    Risk Class Breakdown
                  </p>
                  {classProbBar('SEVERE', data.class_probabilities.SEVERE, 25)}
                  {classProbBar('HIGH', data.class_probabilities.HIGH, 25)}
                  {classProbBar('MODERATE', data.class_probabilities.MODERATE, 25)}
                  {classProbBar('LOW', 100 - data.flood_probability, 100)}
                </div>
                <div>
                  <p className="mb-2 text-sm font-medium text-flood-text">
                    Location Details
                  </p>
                  <dl className="text-sm">
                    <dt className="text-flood-muted">Latitude</dt>
                    <dd>{data.latitude.toFixed(4)}°</dd>
                    <dt className="text-flood-muted">Longitude</dt>
                    <dd>{data.longitude.toFixed(4)}°</dd>
                    <dt className="text-flood-muted">Elevation</dt>
                    <dd>{data.elevation_m.toFixed(1)} m</dd>
                    <dt className="text-flood-muted">Soil Moisture</dt>
                    <dd>{data.soil_moisture.toFixed(3)}</dd>
                  </dl>
                </div>
              </div>

              <div className="mt-6 text-sm text-flood-muted">
                <p>
                  Source: {data.source} · Last updated: {formatTime(data.fetch_timestamp)}
                  {data.weather_timestamp && (
                    <span>
                      {' · Weather at: '}
                      {formatTime(data.weather_timestamp)}
                    </span>
                  )}
                </p>
                {data.stale && (
                  <p className="mt-1 font-medium text-amber-400">
                    ⚠ Showing cached data — unable to fetch fresh readings
                  </p>
                )}
              </div>
            </div>
          </section>
        )}

        {data && (
          <section
            className="mb-8 rounded-lg border border-flood-border bg-flood-panel p-6"
            aria-label="Model and methodology"
          >
            <h3 className="mb-2 text-lg font-semibold text-flood-text">
              Model & Methodology
            </h3>
            <p className="text-sm text-flood-muted">
              <span className="font-medium text-flood-text">Method:</span>{' '}
              {data.method === 'random_forest'
                ? 'Random Forest (ML)'
                : 'Heuristic rules'}
            </p>
            <p className="mt-2 text-sm text-flood-muted">
              {data.model_limitations}
            </p>
          </section>
        )}

        <section className="mb-8" aria-label="Monitored locations">
          <h2 className="mb-4 text-xl font-semibold text-flood-text">
            Monitored Locations
          </h2>

          <div className="mb-4 rounded-lg border border-flood-border bg-flood-panel-2 p-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
              <input
                type="text"
                placeholder="Name"
                value={addName}
                onChange={(e) => setAddName(e.target.value)}
                aria-label="Monitor name"
                className="rounded-md border border-flood-border bg-flood-bg px-3 py-2 text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
              />
              <input
                type="number"
                placeholder="Lat"
                step="0.0001"
                value={addLat}
                onChange={(e) => setAddLat(e.target.value)}
                aria-label="Monitor latitude"
                className="rounded-md border border-flood-border bg-flood-bg px-3 py-2 text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
              />
              <input
                type="number"
                placeholder="Lon"
                step="0.0001"
                value={addLon}
                onChange={(e) => setAddLon(e.target.value)}
                aria-label="Monitor longitude"
                className="rounded-md border border-flood-border bg-flood-bg px-3 py-2 text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
              />
              <input
                type="number"
                placeholder="Threshold (%)"
                step="1"
                min="0"
                max="100"
                value={addThreshold}
                onChange={(e) => setAddThreshold(e.target.value)}
                aria-label="Alert threshold"
                className="rounded-md border border-flood-border bg-flood-bg px-3 py-2 text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
              />
              <button
                type="button"
                onClick={handleAddMonitor}
                className="rounded-md border border-flood-border bg-flood-accent px-4 py-2 font-medium text-flood-bg hover:bg-flood-accent/80"
              >
                Add
              </button>
            </div>
          </div>

          {monitorsLoading && (
            <p className="text-flood-muted">Loading monitors...</p>
          )}
          {monitorError && (
            <p className="mb-2 text-red-300">{monitorError}</p>
          )}
          {monitors.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-flood-border bg-flood-panel">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="p-3 text-left text-sm text-flood-muted">
                      Name
                    </th>
                    <th className="p-3 text-left text-sm text-flood-muted">
                      Location
                    </th>
                    <th className="p-3 text-left text-sm text-flood-muted">
                      Threshold
                    </th>
                    <th className="p-3 text-left text-sm text-flood-muted">
                      Last Risk
                    </th>
                    <th className="p-3 text-left text-sm text-flood-muted">
                      Probability
                    </th>
                    <th className="p-3 text-left text-sm text-flood-muted">
                      Alert
                    </th>
                    <th className="p-3 text-center text-sm text-flood-muted">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {monitors.map((m) => (
                    <tr
                      key={m.id}
                      className="border-t border-flood-border"
                    >
                      <td className="p-3">{m.name}</td>
                      <td className="p-3 text-flood-muted">
                        {m.lat.toFixed(4)}, {m.lon.toFixed(4)}
                      </td>
                      <td className="p-3">{m.threshold}%</td>
                      <td className="p-3">
                        {m.last_band ? (
                          <span
                            className={`rounded px-2 py-1 text-xs font-bold ${RISK_BADGE_CLASS[m.last_band]}`}
                          >
                            {m.last_band}
                          </span>
                        ) : (
                          '--'
                        )}
                      </td>
                      <td className="p-3 text-flood-muted">
                        {m.last_probability != null
                          ? `${m.last_probability.toFixed(1)}%`
                          : '--'}
                      </td>
                      <td className="p-3">
                        {m.alert ? (
                          <span className="font-medium text-red-400">
                            ⚠ Active
                          </span>
                        ) : (
                          'No'
                        )}
                      </td>
                      <td className="p-3 text-center">
                        <button
                          type="button"
                          onClick={() => void handleDeleteMonitor(m.id)}
                          className="text-flood-muted hover:text-flood-text"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <footer className="border-t border-flood-border pt-6 text-sm text-flood-muted">
          <p className="font-medium text-amber-400">⚠ Disclaimer</p>
          <p className="mt-1">
            Floodsense is an early-warning information tool only. Its flood
            probability estimates come from a model trained on synthetic
            rainfall data combined with publicly available weather readings. It
            is NOT a substitute for official flood warnings, emergency services,
            or real-time monitoring. Always follow guidance from your local
            emergency management authority and evacuate immediately if advised.
          </p>
        </footer>
      </div>
    </div>
  )
}
