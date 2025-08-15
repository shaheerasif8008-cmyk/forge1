"use client";

import { useEffect, useRef, useState } from "react";

interface UseSSEOptions {
  url: string;
  enabled?: boolean;
  onMessage?: (data: unknown) => void;
  onError?: (error: Event) => void;
}

interface UseSSEReturn {
  data: unknown[];
  isConnected: boolean;
  error: string | null;
  reconnect: () => void;
}

export function useSSE({
  url,
  enabled = true,
  onMessage,
  onError,
}: UseSSEOptions): UseSSEReturn {
  const [data, setData] = useState<unknown[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);

  const connect = () => {
    if (!enabled || !url) return;

    try {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data);
          setData((prev) => [parsedData, ...prev.slice(0, 99)]);
          onMessage?.(parsedData);
        } catch {
          setData((prev) => [event.data, ...prev.slice(0, 99)]);
          onMessage?.(event.data);
        }
      };

      eventSource.onerror = (event) => {
        setIsConnected(false);
        setError("Connection lost");
        onError?.(event);

        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current += 1;

        reconnectTimeoutRef.current = setTimeout(() => {
          if (enabled) {
            connect();
          }
        }, delay);
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect");
      setIsConnected(false);
    }
  };

  const reconnect = () => {
    reconnectAttempts.current = 0;
    connect();
  };

  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [url, enabled]);

  return {
    data,
    isConnected,
    error,
    reconnect,
  };
}