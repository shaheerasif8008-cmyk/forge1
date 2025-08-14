import { useEffect, useState } from 'react';
import { useSession } from '../components/SessionManager';
import config from '../config';

type Metrics = {
  count: number;
  pass: number;
  fail: number;
  avg_latency_ms: number | null;
  tokens_in: number;
  tokens_out: number;
  est_cost_usd: number;
  events: Array<{
    tenant_id: string;
    feature: string;
    status: string;
    tokens_in?: number;
    tokens_out?: number;
    latency_ms?: number;
    ts: string;
  }>;
};

export default function MetricsPage() {
  const [data, setData] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { token } = useSession();

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        if (!token) {
          throw new Error('Not authenticated');
        }
        const res = await fetch(`${config.apiUrl}/api/v1/metrics/beta`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Failed to load metrics');
        const json = await res.json();
        setData(json);
        try { localStorage.setItem('forge_last_metrics', JSON.stringify(json)); } catch {}
      } catch (e: any) {
        // Try last-good cache
        try {
          const cached = localStorage.getItem('forge_last_metrics');
          if (cached) {
            setData(JSON.parse(cached));
            setError(null);
            return;
          }
        } catch {}
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  if (loading) return <div className="p-4">Loading metrics…</div>;
  if (error) return <div className="p-4 text-red-600">{error}</div>;
  if (!data) return <div className="p-4">No data</div>;

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Beta Metrics</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Events" value={data.count} />
        <Stat label="Pass" value={data.pass} />
        <Stat label="Fail" value={data.fail} />
        <Stat label="Avg Latency (ms)" value={data.avg_latency_ms ?? '-'} />
        <Stat label="Tokens In" value={data.tokens_in} />
        <Stat label="Tokens Out" value={data.tokens_out} />
        <Stat label="Est. Cost ($)" value={data.est_cost_usd} />
      </div>

      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th className="py-2 pr-4">Time</th>
            <th className="py-2 pr-4">Tenant</th>
            <th className="py-2 pr-4">Feature</th>
            <th className="py-2 pr-4">Status</th>
            <th className="py-2 pr-4">Latency</th>
            <th className="py-2 pr-4">Tokens</th>
          </tr>
        </thead>
        <tbody>
          {data.events.map((e, idx) => (
            <tr key={idx} className="border-b">
              <td className="py-2 pr-4">{new Date(e.ts).toLocaleString()}</td>
              <td className="py-2 pr-4">{e.tenant_id}</td>
              <td className="py-2 pr-4">{e.feature}</td>
              <td className="py-2 pr-4">{e.status}</td>
              <td className="py-2 pr-4">{e.latency_ms ?? '-'}</td>
              <td className="py-2 pr-4">{(e.tokens_in ?? 0) + (e.tokens_out ?? 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div className="p-3 rounded border">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-medium">{String(value)}</div>
    </div>
  );
}


