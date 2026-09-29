import { RISK_BADGE_CLASS, bandLabel, formatTime } from '../format';
import type { FloodProbabilityResponse, RiskBand } from '../types';

export default function RiskGauge({ data }: { data: FloodProbabilityResponse }) {
  const bandClass = RISK_BADGE_CLASS[data.risk_band] ?? RISK_BADGE_CLASS.LOW;

  return (
    <div className="rounded-lg border border-flood-border bg-flood-panel p-6">
      <p className="text-sm uppercase text-flood-muted">Flood Probability</p>
      <div className="mt-2 flex items-baseline gap-4">
        <span className="text-6xl font-bold text-flood-text">
          {data.flood_probability.toFixed(1)}%
        </span>
        <span
          className={`rounded-full px-4 py-1 text-lg font-bold ${bandClass}`}
          aria-label={`Risk level: ${data.risk_band}`}
        >
          {bandLabel(data.risk_band as RiskBand)}
        </span>
      </div>

      {data.location_name && (
        <p className="mt-2 text-sm text-flood-muted">{data.location_name}</p>
      )}

      <div className="mt-4 text-xs text-flood-muted">
        Source: {data.source}
        {' · Last updated: '}
        {formatTime(data.fetch_timestamp)}
        {data.weather_timestamp && (
          <span>
            {' · Weather at: '}
            {formatTime(data.weather_timestamp)}
          </span>
        )}
      </div>

      {data.stale && (
        <p className="mt-1 text-xs font-medium text-amber-400">
          Showing cached data — unable to fetch fresh readings
        </p>
      )}
    </div>
  );
}
