import { useEffect, useState, useCallback, useRef } from 'react';
import { fetchFloodProbability } from '../api';
import type { FloodProbabilityResponse } from '../types';

const POLL_INTERVAL = 600_000; // 10 minutes

export function useFloodProbability(
  lat: number,
  lon: number,
  locationName?: string,
) {
  const [data, setData] = useState<FloodProbabilityResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchData = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchFloodProbability(lat, lon, locationName, signal);
        setData(result);
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    },
    [lat, lon, locationName],
  );

  useEffect(() => {
    const controller = new AbortController();
    abortRef.current = controller;
    void fetchData(controller.signal);
    return () => controller.abort();
  }, [fetchData]);

  useEffect(() => {
    const interval = setInterval(() => {
      const controller = new AbortController();
      abortRef.current = controller;
      void fetchData(controller.signal);
    }, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  const refresh = useCallback(() => {
    const controller = new AbortController();
    abortRef.current = controller;
    void fetchData(controller.signal);
  }, [fetchData]);

  return { data, loading, error, refresh };
}
