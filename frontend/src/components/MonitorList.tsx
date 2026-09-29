import type { MonitoredLocation } from '../types';
import { RISK_BADGE_CLASS } from '../format';

export interface MonitorListProps {
  monitors: MonitoredLocation[];
  onRemove: (id: number) => void;
  loading: boolean;
}

export default function MonitorList({ monitors, onRemove, loading }: MonitorListProps) {
  if (loading) {
    return <p className="text-sm text-flood-muted">Loading monitors...</p>;
  }

  if (monitors.length === 0) {
    return (
      <p className="text-sm text-flood-muted">
        No monitored locations. Add one below.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {monitors.map((m) => {
        const badgeClass = m.last_band
          ? RISK_BADGE_CLASS[m.last_band]
          : 'badge-low';
        return (
          <div
            key={m.id}
            className="flex items-center justify-between rounded-md border border-flood-border bg-flood-panel-2 p-3"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-flood-text">{m.name}</span>
                {m.last_band && (
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-bold ${badgeClass}`}
                  >
                    {m.last_band}
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-flood-muted">
                {m.lat.toFixed(4)}°, {m.lon.toFixed(4)}° · Threshold: {m.threshold}%
                {m.last_probability !== null && (
                  <span className="mx-1">· {m.last_probability.toFixed(1)}%</span>
                )}
              </p>
              {m.alert && (
                <span className="mt-1 text-xs font-medium text-red-400">
                  Alert: probability exceeds threshold
                </span>
              )}
              {m.stale && (
                <p className="mt-1 text-xs text-amber-400">
                  Showing stale cached data
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => onRemove(m.id)}
              className="ml-2 rounded-md border border-flood-border px-2 py-1 text-xs text-flood-muted hover:text-flood-text"
              aria-label={`Remove ${m.name}`}
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}
