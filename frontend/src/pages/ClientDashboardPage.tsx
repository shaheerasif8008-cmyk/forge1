import { useEffect, useMemo, useRef, useState } from "react";
import { useSession } from "../components/SessionManager";
import config from "../config";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type Summary = {
  tasks: number;
  avg_duration_ms: number;
  success_ratio: number;
  tokens: number;
  cost_cents: number;
  by_day: Array<{
    day: string;
    tasks: number;
    avg_duration_ms: number | null;
    success_ratio: number | null;
    tokens: number;
    errors: number;
  }>;
};

export default function ClientDashboardPage() {
  const { token } = useSession();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [, setLoading] = useState(true);
  const esRef = useRef<EventSource | null>(null);

  const headers = useMemo(
    () => ({
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }),
    [token],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${config.apiUrl}/api/v1/client/metrics/summary?hours=24`, {
          headers,
        });
        if (res.ok) setSummary(await res.json());
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [headers]);

  useEffect(() => {
    if (!token) return;
    const url = new URL(`${config.apiUrl}/api/v1/ai-comms/events`);
    url.searchParams.set("token", token);
    const es = new EventSource(url.toString());
    esRef.current = es;
    es.addEventListener("message", (ev) => {
      try {
        const data = JSON.parse((ev as MessageEvent).data as string);
        setEvents((prev) => {
          const next = [data, ...prev];
          return next.slice(0, 100);
        });
      } catch {}
    });
    es.onerror = () => {
      // auto-reconnect by replacing the EventSource
      es.close();
      esRef.current = null;
      setTimeout(() => {
        if (!esRef.current) {
          const retry = new EventSource(url.toString());
          esRef.current = retry;
        }
      }, 2000);
    };
    return () => {
      es.close();
      esRef.current = null;
    };
  }, [token]);

  const cards = [
    { label: "Active employees", value: "—" },
    { label: "24h runs", value: summary ? String(summary.tasks) : "—" },
    {
      label: "Success %",
      value: summary ? `${Math.round((summary.success_ratio || 0) * 100)}%` : "—",
    },
    {
      label: "p95 latency",
      value: summary ? `${Math.round((summary.avg_duration_ms || 0) * 1.5)} ms` : "—",
    },
    { label: "Tokens", value: summary ? String(summary.tokens) : "—" },
    { label: "Cost est.", value: summary ? `$${(summary.cost_cents / 100).toFixed(2)}` : "—" },
  ];

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded shadow p-3">
            <div className="text-xs text-gray-500">{c.label}</div>
            <div className="text-xl font-semibold">{c.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="bg-white rounded shadow p-4 xl:col-span-2">
          <div className="text-sm font-medium mb-2">Usage over time</div>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <LineChart data={(summary?.by_day || []).slice().reverse()}>
                <CartesianGrid stroke="#eee" strokeDasharray="5 5" />
                <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line type="monotone" dataKey="tasks" stroke="#2563eb" strokeWidth={2} />
                <Line type="monotone" dataKey="errors" stroke="#dc2626" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded shadow p-4">
          <div className="text-sm font-medium mb-2">Live activity</div>
          <div className="max-h-[280px] overflow-auto space-y-2">
            {events.map((e, idx) => (
              <div key={idx} className="border rounded p-2 text-xs">
                <div className="flex justify-between">
                  <div className="font-medium">{e.type}</div>
                  <div className="text-gray-500">{e.time || ""}</div>
                </div>
                <div className="text-gray-600 break-words">
                  {e.data ? JSON.stringify(e.data) : "(no data)"}
                </div>
              </div>
            ))}
            {!events.length && <div className="text-xs text-gray-500">Waiting for events…</div>}
          </div>
        </div>
      </div>
    </div>
  );
}


