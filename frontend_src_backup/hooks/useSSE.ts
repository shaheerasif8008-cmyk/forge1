"use client";

import { useEffect, useRef, useState } from "react";

export type UseSSEOptions = {
  url: string;
  withCredentials?: boolean;
};

export function useSSE<T = unknown>({ url, withCredentials }: UseSSEOptions) {
  const [data, setData] = useState<T[]>([]);
  const [error, setError] = useState<unknown>(null);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!url) return;
    try {
      const es = new EventSource(url, { withCredentials });
      sourceRef.current = es;
      es.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as T;
          setData((prev) => [...prev, parsed]);
        } catch {
          setData((prev) => [...prev, (event.data as unknown) as T]);
        }
      };
      es.onerror = (e) => {
        setError(e);
      };
    } catch (e) {
      setError(e);
    }
    return () => {
      try {
        sourceRef.current?.close();
      } catch {}
      sourceRef.current = null;
    };
  }, [url, withCredentials]);

  return { data, error } as const;
}


