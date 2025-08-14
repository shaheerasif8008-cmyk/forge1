import { useEffect, useMemo, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { useSession } from '../components/SessionManager';
import config from '../config';

type Summary = {
  tasks: number;
  avg_duration_ms: number;
  tokens: number;
  tool_calls: number;
  errors: number;
  success_ratio: number;
};

type ByDay = {
  day: string;
  tenant_id: string;
  employee_id: string | null;
  tasks: number;
  avg_duration_ms: number | null;
  tokens: number;
  tool_calls: number;
  errors: number;
  success_ratio: number | null;
};

type MetricsResponse = {
  summary: Summary;
  by_day: ByDay[];
};

export default function AdminMonitoringPage() {
  const { token, user } = useSession();
  const [tenant, setTenant] = useState<string>('');
  const [from, setFrom] = useState<string>('');
  const [to, setTo] = useState<string>('');
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = useMemo(() => (user?.role === 'admin'), [user]);

  useEffect(() => {
    if (!isAdmin) return;
    void load();
    const id = setInterval(()=>{ void load(); }, 15000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenant, from, to, token, isAdmin]);

  const load = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (tenant) params.set('tenant_id', tenant);
      // convert date range to year/month filters for backend (simple version)
      if (from) {
        const d = new Date(from); params.set('year', String(d.getUTCFullYear())); params.set('month', String(d.getUTCMonth()+1));
      }
      if (to && !from) {
        const d = new Date(to); params.set('year', String(d.getUTCFullYear())); params.set('month', String(d.getUTCMonth()+1));
      }
      const res = await fetch(`${config.apiUrl}/api/v1/metrics?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load metrics');
      const json = await res.json() as MetricsResponse;
      setData(json);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isAdmin) return <div className="p-4 text-red-600">Admin access required.</div>;
  if (loading) return <div className="p-4">Loading…</div>;

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Monitoring & Metrics</h1>

      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500">Tenant</label>
          <input value={tenant} onChange={(e)=>setTenant(e.target.value)} placeholder="tenant id" className="border rounded px-2 py-1" />
        </div>
        <div>
          <label className="block text-xs text-gray-500">From</label>
          <input type="date" value={from} onChange={(e)=>setFrom(e.target.value)} className="border rounded px-2 py-1" />
        </div>
        <div>
          <label className="block text-xs text-gray-500">To</label>
          <input type="date" value={to} onChange={(e)=>setTo(e.target.value)} className="border rounded px-2 py-1" />
        </div>
        <button onClick={()=>void load()} className="px-3 py-1 rounded bg-blue-600 text-white">Refresh</button>
      </div>

      {error && <div className="text-red-600">{error}</div>}

      {data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Stat label="Total Tasks" value={data.summary.tasks} />
            <Stat label="Avg Duration (ms)" value={Math.round(data.summary.avg_duration_ms)} />
            <Stat label="Tokens" value={data.summary.tokens} />
            <Stat label="Tool Calls" value={data.summary.tool_calls} />
            <Stat label="Errors" value={data.summary.errors} />
          </div>

          <section>
            <h2 className="font-semibold mb-2">Task Success Ratio</h2>
            <div className="h-2 bg-gray-200 rounded">
              <div className="h-2 bg-green-500 rounded" style={{ width: `${(data.summary.success_ratio*100).toFixed(1)}%` }} />
            </div>
            <div className="text-xs text-gray-600 mt-1">{(data.summary.success_ratio*100).toFixed(1)}%</div>
          </section>

          <section>
            <h2 className="font-semibold mb-2">Token Usage (by day)</h2>
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.by_day} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="tokens" name="Tokens" stroke="#3b82f6" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section>
            <h2 className="font-semibold mb-2">Success vs Errors (by day)</h2>
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.by_day} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="tasks" name="Tasks" stackId="a" fill="#10b981" />
                  <Bar dataKey="errors" name="Errors" stackId="a" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <ActiveEmployees tenant={tenant} />

          <section>
            <h2 className="font-semibold mb-2">Recent Error Logs (24h)</h2>
            <ErrorLogs token={token!} tenant={tenant} />
          </section>
        </div>
      )}
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

function ErrorLogs({ token, tenant }: { token: string; tenant?: string }) {
  const [rows, setRows] = useState<Array<{ ts: string; path: string; status: number; user_id?: number }>>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string|undefined>();

  useEffect(()=>{
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, tenant]);

  const load = async () => {
    setLoading(true);
    setErr(undefined);
    try {
      const qs = new URLSearchParams();
      qs.set('limit', '50');
      qs.set('since_hours', '24');
      if (tenant) qs.set('tenant_id', tenant);
      const res = await fetch(`${config.apiUrl}/api/v1/logs?${qs.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load logs');
      const data = await res.json() as Array<{ timestamp?: string; path?: string; status_code?: number; user_id?: number }>;
      setRows(data.map(d => ({ ts: d.timestamp || '', path: d.path || '', status: d.status_code || 0, user_id: d.user_id })));
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading…</div>;
  if (err) return <div className="text-red-600">{err}</div>;
  if (!rows.length) return <div>No errors</div>;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-[600px] text-sm">
        <thead>
          <tr className="text-left border-b">
            <th className="py-2 pr-4">Time</th>
            <th className="py-2 pr-4">Path</th>
            <th className="py-2 pr-4">Status</th>
            <th className="py-2 pr-4">User</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i)=> (
            <tr key={i} className="border-b">
              <td className="py-2 pr-4">{new Date(r.ts).toLocaleString()}</td>
              <td className="py-2 pr-4">{r.path}</td>
              <td className="py-2 pr-4">{r.status}</td>
              <td className="py-2 pr-4">{r.user_id ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActiveEmployees({ tenant }: { tenant?: string }) {
  const { token } = useSession();
  const [count, setCount] = useState<number>(0);
  useEffect(() => {
    if (!token) return;
    let mounted = true;
    const load = async () => {
      const qs = new URLSearchParams();
      qs.set('minutes', '5');
      if (tenant) qs.set('tenant_id', tenant);
      const res = await fetch(`${config.apiUrl}/api/v1/metrics/active?${qs.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const j = await res.json() as { active_employees: number };
        if (mounted) setCount(j.active_employees);
      }
    };
    void load();
    const id = setInterval(load, 15000);
    return () => { mounted = false; clearInterval(id); };
  }, [token, tenant]);
  return (
    <section>
      <h2 className="font-semibold mb-2">Active Employees (5m)</h2>
      <div className="text-2xl">{count}</div>
    </section>
  );
}

