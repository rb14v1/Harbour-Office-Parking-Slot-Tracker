import { useCallback, useEffect, useRef, useState } from 'react';

export const POLL_INTERVAL_MS = 5000;

/**
 * Loads data now and then every `intervalMs`. Pauses while the browser tab is hidden.
 * `deps` restarts the loader when filters change.
 */
export function usePolling(loader, deps = [], intervalMs = POLL_INTERVAL_MS) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const refresh = useCallback(async () => {
    try {
      const data = await loaderRef.current();
      setState({ data, error: null, loading: false });
    } catch (error) {
      setState((previous) => ({ ...previous, error, loading: false }));
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(() => {
      if (!document.hidden) refresh();
    }, intervalMs);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, intervalMs, ...deps]);

  return { ...state, refresh };
}
