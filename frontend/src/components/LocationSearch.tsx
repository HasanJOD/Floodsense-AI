import { useState, useCallback } from 'react';
import { geocodeSearch } from '../api';
import type { GeocodeResult } from '../types';

export interface LocationSearchProps {
  onLocationSelect: (lat: number, lon: number, name?: string) => void;
  currentLat: number;
  currentLon: number;
}

export default function LocationSearch({
  onLocationSelect,
  currentLat,
  currentLon,
}: LocationSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const handleSelect = useCallback(
    (result: GeocodeResult) => {
      onLocationSelect(result.latitude, result.longitude, result.name);
      setQuery('');
      setResults([]);
      setShowResults(false);
    },
    [onLocationSelect],
  );

  const handleSearch = useCallback(async (q: string) => {
    setQuery(q);
    if (q.length < 2) {
      setResults([]);
      setShowResults(false);
      return;
    }
    setIsSearching(true);
    try {
      const res = await geocodeSearch(q);
      setResults(res.results);
      setShowResults(true);
    } catch {
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  return (
    <div className="relative mb-4">
      <input
        type="text"
        placeholder="Search a location..."
        value={query}
        onChange={(e) => void handleSearch(e.target.value)}
        onFocus={() => results.length > 0 && setShowResults(true)}
        onBlur={() => setTimeout(() => setShowResults(false), 200)}
        className="w-full rounded-md border border-flood-border bg-flood-bg px-3 py-2 text-flood-text focus:outline-none focus:ring-2 focus:ring-flood-accent"
        aria-label="Search location"
        autoComplete="off"
      />
      {showResults && results.length > 0 && (
        <ul
          className="absolute z-[1000] mt-1 max-h-48 w-full overflow-y-auto rounded-md border border-flood-border bg-flood-panel-2 shadow-lg"
          role="listbox"
        >
          {results.map((r) => (
            <button
              key={`${r.latitude},${r.longitude}`}
              type="button"
              onMouseDown={() => handleSelect(r)}
              className="w-full px-3 py-2 text-left text-sm text-flood-text hover:bg-flood-border"
            >
              {r.name}
            </button>
          ))}
        </ul>
      )}
      {isSearching && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-flood-muted">
          Searching...
        </div>
      )}
      {currentLat !== 0 && currentLon !== 0 && (
        <p className="mt-1 text-xs text-flood-muted">
          Current view: {currentLat.toFixed(4)}°, {currentLon.toFixed(4)}°
        </p>
      )}
    </div>
  );
}
