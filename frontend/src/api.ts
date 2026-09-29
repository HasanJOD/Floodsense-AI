import type {
  FloodProbabilityResponse,
  FloodGridResponse,
  GeocodeResponse,
  MonitoredListResponse,
  MonitoredLocation,
  MonitoredLocationInput,
  MapBounds,
} from './types';

async function getJSON<T>(
  path: string,
  params: Record<string, string> = {},
  signal?: AbortSignal,
): Promise<T> {
  const url = new URL(path, window.location.origin);
  for (const [k, v] of Object.entries(params)) {
    url.searchParams.set(k, v);
  }
  const res = await fetch(url, { headers: { Accept: 'application/json' }, signal });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${path} failed (${res.status}): ${text}`);
  }
  return (await res.json()) as T;
}

export async function fetchFloodProbability(
  lat: number,
  lon: number,
  locationName?: string,
  signal?: AbortSignal,
): Promise<FloodProbabilityResponse> {
  const params: Record<string, string> = {
    lat: String(lat),
    lon: String(lon),
  };
  if (locationName) params.location_name = locationName;
  return getJSON<FloodProbabilityResponse>('/flood-probability', params, signal);
}

export async function fetchFloodGrid(
  bounds: MapBounds,
  res: number,
  signal?: AbortSignal,
): Promise<FloodGridResponse> {
  return getJSON<FloodGridResponse>('/flood-grid', {
    north: String(bounds.north),
    south: String(bounds.south),
    east: String(bounds.east),
    west: String(bounds.west),
    res: String(res),
  }, signal);
}

export async function geocodeSearch(
  q: string,
  signal?: AbortSignal,
): Promise<GeocodeResponse> {
  return getJSON<GeocodeResponse>('/geocode', { q }, signal);
}

export async function listMonitored(): Promise<MonitoredLocation[]> {
  const res = await getJSON<MonitoredListResponse>('/monitor');
  return res.locations;
}

export async function addMonitor(
  input: MonitoredLocationInput,
): Promise<MonitoredLocation> {
  const res = await fetch('/monitor', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`add monitor failed (${res.status}): ${text}`);
  }
  return (await res.json()) as MonitoredLocation;
}

export async function deleteMonitor(id: number): Promise<void> {
  const res = await fetch(`/monitor/${id}`, { method: 'DELETE' });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`delete monitor failed (${res.status}): ${text}`);
  }
}
