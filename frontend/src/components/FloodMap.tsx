import { useEffect, useRef } from 'react';
import {
  MapContainer,
  Marker,
  Tooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import LayerSwitcher from './LayerSwitcher';
import RiskOverlay from './RiskOverlay';
import type { FloodGridResponse, MonitoredLocation, RiskBand } from '../types';

export interface FloodMapProps {
  center: [number, number];
  zoom: number;
  onSelectPoint: (lat: number, lon: number) => void;
  onMove: (lat: number, lon: number) => void;
  selectedPoint: [number, number] | null;
  grid: FloodGridResponse | null;
  monitors: MonitoredLocation[];
}

const CENTER_EPSILON = 1e-4;

function MapClickHandler({ onSelect }: { onSelect: (lat: number, lon: number) => void }) {
  useMapEvents({
    click: (e) => {
      const { lat, lng } = e.latlng;
      onSelect(lat, lng);
    },
  });
  return null;
}

/**
 * Bridges the map and the `center` prop.
 *
 * The map is the source of truth while the user pans or clicks, so those
 * updates are reported upward and must not be animated back. Only centers that
 * originate elsewhere (location search, geolocation) trigger a flyTo.
 */
function MapCenterController(props: {
  center: [number, number];
  onMove: (lat: number, lon: number) => void;
}) {
  const map = useMap();
  const selfCenterRef = useRef<[number, number] | null>(null);
  const { center, onMove } = props;
  const targetLat = center[0];
  const targetLng = center[1];

  useMapEvents({
    moveend: () => {
      const c = map.getCenter();
      selfCenterRef.current = [c.lat, c.lng];
      onMove(c.lat, c.lng);
    },
    click: (e) => {
      selfCenterRef.current = [e.latlng.lat, e.latlng.lng];
    },
  });

  useEffect(() => {
    const self = selfCenterRef.current;
    if (
      self &&
      Math.abs(self[0] - targetLat) <= CENTER_EPSILON &&
      Math.abs(self[1] - targetLng) <= CENTER_EPSILON
    ) {
      return;
    }
    map.flyTo([targetLat, targetLng], map.getZoom(), { duration: 0.6 });
  }, [map, targetLat, targetLng]);

  return null;
}

function makeMonitorIcon(band: RiskBand | null, alert: boolean): L.DivIcon {
  const color = bandToHex(band);
  const html = alert
    ? `<div class="alert-pulse h-3.5 w-3.5 rounded-full" style="background-color: ${color};"></div>`
    : `<div class="h-3 w-3 rounded-full" style="background-color: ${color}; border: 2px solid white;"></div>`;
  return L.divIcon({
    className: 'monitor-marker',
    html,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

function makeSelectedIcon(): L.DivIcon {
  return L.divIcon({
    className: 'selected-marker',
    html: '<div class="h-4 w-4 rounded-full border-2 border-cyan-400 bg-cyan-400"></div>',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

function bandToHex(band: RiskBand | null): string {
  if (!band) return '#ffffff';
  const colors: Record<string, string> = {
    LOW: '#22c55e',
    MODERATE: '#eab308',
    HIGH: '#f97316',
    SEVERE: '#ef4444',
  };
  return colors[band] ?? '#ffffff';
}

export default function FloodMap({
  center,
  zoom,
  onSelectPoint,
  onMove,
  selectedPoint,
  grid,
  monitors,
}: FloodMapProps) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      style={{ height: '100%', width: '100%' }}
      scrollWheelZoom={true}
    >
      <LayerSwitcher />
      <RiskOverlay grid={grid} />
      <MapClickHandler onSelect={onSelectPoint} />
      <MapCenterController center={center} onMove={onMove} />

      {selectedPoint && (
        <Marker
          position={[selectedPoint[0], selectedPoint[1]]}
          icon={makeSelectedIcon()}
        >
          <Tooltip direction="top" offset={[0, -10]} opacity={0.9}>
            Selected point
          </Tooltip>
        </Marker>
      )}

      {monitors.map((m) => (
        <Marker
          key={m.id}
          position={[m.lat, m.lon]}
          icon={makeMonitorIcon(m.last_band, m.alert)}
        >
          <Tooltip direction="top" offset={[0, -12]} opacity={0.9}>
            <div className="text-xs">
              <strong>{m.name}</strong>
              <br />
              {m.last_probability != null
                ? `${m.last_probability.toFixed(1)}% — ${m.last_band ?? '—'}`
                : '—'}
              {m.alert && <span className="block text-red-400">⚠ Alert</span>}
            </div>
          </Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}
