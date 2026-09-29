import { useState, useCallback, useEffect } from 'react';
import { listMonitored, addMonitor, deleteMonitor } from '../api';
import type { MonitoredLocation, MonitoredLocationInput } from '../types';

export function useMonitors() {
  const [monitors, setMonitors] = useState<MonitoredLocation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mutateError, setMutateError] = useState<string | null>(null);
  const POLL_INTERVAL = 600_000;

  const fetchMonitors = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listMonitored();
      setMonitors(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const add = useCallback(async (input: MonitoredLocationInput) => {
    setMutateError(null);
    try {
      const monitor = await addMonitor(input);
      setMonitors((prev) => [...prev, monitor]);
      return monitor;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setMutateError(message);
      throw err;
    }
  }, []);

  const remove = useCallback(async (id: number) => {
    setMutateError(null);
    try {
      await deleteMonitor(id);
      setMonitors((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setMutateError(message);
      // A monitor that is already gone should still disappear from the list.
      await fetchMonitors();
    }
  }, [fetchMonitors]);

  useEffect(() => {
    void fetchMonitors();
    const interval = setInterval(() => {
      void fetchMonitors();
    }, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchMonitors]);

  return { monitors, loading, error, mutateError, add, remove, refresh: fetchMonitors };
}
