import type React from 'react';
import type { RiskBand } from './types';

export function formatTime(ts: string | null): string {
  if (!ts) return '--';
  return new Date(ts).toLocaleString();
}

export const RISK_BADGE_CLASS: Record<RiskBand, string> = {
  LOW: 'badge-low',
  MODERATE: 'badge-moderate',
  HIGH: 'badge-high',
  SEVERE: 'badge-severe',
};

export function bandColor(band: RiskBand): string {
  return `var(--color-risk-${band.toLowerCase()})`;
}

export function bandLabel(band: RiskBand): string {
  const labels: Record<RiskBand, string> = {
    LOW: 'Low',
    MODERATE: 'Moderate',
    HIGH: 'High',
    SEVERE: 'Severe',
  };
  return labels[band];
}

export const RISK_BANDS: RiskBand[] = ['LOW', 'MODERATE', 'HIGH', 'SEVERE'];

export function classProbBar(
  label: RiskBand,
  value: number,
  max: number,
): React.ReactElement {
  const pct = max > 0 ? (value / max) * 100 : 0;
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
            backgroundColor: bandColor(label),
          }}
        />
      </div>
    </div>
  );
}
