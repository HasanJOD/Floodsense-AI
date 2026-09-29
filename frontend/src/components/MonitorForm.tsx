import { useState } from 'react';
import type { MonitoredLocationInput } from '../types';

export interface MonitorFormProps {
  onAdd: (input: MonitoredLocationInput) => Promise<unknown>;
  error: string | null;
}

export default function MonitorForm({ onAdd, error }: MonitorFormProps) {
  const [name, setName] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [threshold, setThreshold] = useState('50');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const parsedLat = Number.parseFloat(lat);
  const parsedLon = Number.parseFloat(lon);
  const parsedThreshold = Number.parseFloat(threshold);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await onAdd({
        name: name.trim(),
        lat: parsedLat,
        lon: parsedLon,
        threshold: Number.isFinite(parsedThreshold) ? parsedThreshold : 50,
      });
      setName('');
      setLat('');
      setLon('');
      setThreshold('50');
    } catch {
      // Surfaced through the shared `error` prop; keep the input for a retry.
    } finally {
      setSubmitting(false);
    }
  };

  const isValid =
    name.trim().length > 0 &&
    Number.isFinite(parsedLat) &&
    Math.abs(parsedLat) <= 90 &&
    Number.isFinite(parsedLon) &&
    Math.abs(parsedLon) <= 180;

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {(formError || error) && <p className="text-xs text-red-300">{formError ?? error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <input
          type="text"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="col-span-2 rounded-md border border-flood-border bg-flood-bg px-3 py-2 text-sm text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
          required
        />
        <input
          type="number"
          placeholder="Lat"
          step="0.0001"
          min="-90"
          max="90"
          value={lat}
          onChange={(e) => setLat(e.target.value)}
          className="rounded-md border border-flood-border bg-flood-bg px-3 py-2 text-sm text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
          required
        />
        <input
          type="number"
          placeholder="Lon"
          step="0.0001"
          min="-180"
          max="180"
          value={lon}
          onChange={(e) => setLon(e.target.value)}
          className="rounded-md border border-flood-border bg-flood-bg px-3 py-2 text-sm text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
          required
        />
        <input
          type="number"
          placeholder="Threshold (%)"
          step="1"
          min="0"
          max="100"
          value={threshold}
          onChange={(e) => setThreshold(e.target.value)}
          className="rounded-md border border-flood-border bg-flood-bg px-3 py-2 text-sm text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
        />
        <button
          type="submit"
          disabled={!isValid || submitting}
          className="rounded-md border border-flood-border bg-flood-accent px-4 py-2 font-medium text-flood-bg hover:bg-flood-accent/80 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? 'Adding...' : 'Add'}
        </button>
      </div>
    </form>
  );
}
