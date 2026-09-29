import {
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  Area,
  AreaChart,
  CartesianGrid,
} from 'recharts';
import type { HourlyPoint } from '../types';
import { formatTime } from '../format';

const data = [
  { time: '2026-01-01T00:00', precipitation: 0 },
  { time: '2026-01-01T01:00', precipitation: 2.4 },
  { time: '2026-01-01T02:00', precipitation: 1.8 },
  { time: '2026-01-01T03:00', precipitation: 0 },
  { time: '2026-01-01T04:00', precipitation: 5.2 },
  { time: '2026-01-01T05:00', precipitation: 3.1 },
  { time: '2026-01-01T06:00', precipitation: 0 },
  { time: '2026-01-01T07:00', precipitation: 0 },
  { time: '2026-01-01T08:00', precipitation: 0 },
  { time: '2026-01-01T09:00', precipitation: 1.0 },
  { time: '2026-01-01T10:00', precipitation: 0 },
  { time: '2026-01-01T11:00', precipitation: 0 },
  { time: '2026-01-01T12:00', precipitation: 0 },
  { time: '2026-01-01T13:00', precipitation: 0 },
  { time: '2026-01-01T14:00', precipitation: 0 },
  { time: '2026-01-01T15:00', precipitation: 0 },
  { time: '2026-01-01T16:00', precipitation: 0 },
  { time: '2026-01-01T17:00', precipitation: 0 },
  { time: '2026-01-01T18:00', precipitation: 0 },
  { time: '2026-01-01T19:00', precipitation: 0 },
  { time: '2026-01-01T20:00', precipitation: 0 },
  { time: '2026-01-01T21:00', precipitation: 0 },
  { time: '2026-01-01T22:00', precipitation: 0 },
  { time: '2026-01-01T23:00', precipitation: 0 },
];

export default function RainChart({
  hourly,
  loading,
}: {
  hourly: HourlyPoint[];
  loading: boolean;
}) {
  const chartData =
    hourly.length > 0
      ? hourly.map((h) => ({
          time: h.time,
          precipitation: h.precipitation,
        }))
      : data;

  if (loading || hourly.length === 0) {
    return (
      <div className="rounded-lg border border-flood-border bg-flood-panel p-6">
        <h3 className="mb-3 text-sm font-semibold text-flood-text">
          Rainfall (last 24h)
        </h3>
        <p className="text-sm text-flood-muted">No hourly data available</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-flood-border bg-flood-panel p-6">
      <h3 className="mb-3 text-sm font-semibold text-flood-text">
        Rainfall (last 24h)
      </h3>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={chartData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
          <CartesianGrid
            stroke="var(--color-flood-border)"
            strokeDasharray="3 3"
            opacity={0.3}
            vertical={false}
          />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 10, fill: 'var(--color-flood-muted)' }}
            tickLine={false}
            axisLine={false}
            interval={4}
          />
          <YAxis
            tick={{ fontSize: 10, fill: 'var(--color-flood-muted)' }}
            axisLine={false}
            tickLine={false}
            domain={[0, 'auto']}
            width={30}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--color-flood-panel-2)',
              border: '1px solid var(--color-flood-border)',
              borderRadius: '6px',
            }}
            labelStyle={{ color: 'var(--color-flood-text)', fontSize: 12 }}
            formatter={(value: number) => [`${value.toFixed(1)} mm`, 'Precipitation']}
            labelFormatter={(label: string) => formatTime(label)}
          />
          <Area
            type="monotone"
            dataKey="precipitation"
            stroke="var(--color-flood-accent)"
            fill="var(--color-flood-accent)"
            fillOpacity={0.2}
            strokeOpacity={0.8}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
