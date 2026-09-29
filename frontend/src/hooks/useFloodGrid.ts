import { useEffect, useState, useCallback, useRef } from 'react';
import { fetchFloodGrid } from '../api';
import type { FloodGridResponse, MapBounds } from '../types';

const DEBOUNCE_MS = 400;
const CHUNK_RES = 6;

interface GridCacheEntry {
  data: FloodGridResponse;
  timestamp: number;
}

function lruKey(bounds: MapBounds): string {
  return `${Math.round(bounds.north * 1000)},${Math.round(bounds.south * 1000)},${Math.round(bounds.east * 1000)},${Math.round(bounds.west * 1000)}`;
}

export function useFloodGrid() {
  const [data, setData] = useState<FloodGridResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<number | null>(null);
  const cacheRef = useRef<Map<string, GridCacheEntry>>(new Map());

  const fetchGrid = useCallback(
    async (bounds: MapBounds, signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchFloodGrid(bounds, CHUNK_RES, signal);
        setData(result);
        const entry: GridCacheEntry = { data: result, timestamp: Date.now() };
        const cache = cacheRef.current;
        cache.set(lruKey(bounds), entry);
        if (cache.size > 400) {
          const oldest = Array.from(cache.entries()).sort((a, b) => a[1].timestamp - b[1].timestamp)[0];
          cache.delete(oldest[0]);
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const requestGrid = useCallback(
    (bounds: MapBounds) => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = window.setTimeout(() => {
        const controller = new AbortController();
        abortRef.current = controller;
        void fetchGrid(bounds, controller.signal);
      }, DEBOUNCE_MS);
    },
    [fetchGrid],
  );

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      abortRef.current?.abort();
    };
  }, []);

  return { data, loading, error, requestGrid };
}
