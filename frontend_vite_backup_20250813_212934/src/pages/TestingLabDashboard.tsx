import { useEffect, useMemo, useState } from "react";
import { listRuns } from "../api/testingApp";
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";

export default function TestingLabDashboard() {
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listRuns();
        if (!cancelled) setRuns(data);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    const id = setInterval(load, 8000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  const pass = runs.filter(r => r.status === 'pass').length;
  const fail = runs.filter(r => r.status === 'fail').length;
  const total = runs.length || 1;
  const passPct = Math.round((pass * 100) / total);

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Testing Lab</h1>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Tile label="Pass %" value={`${passPct}%`} />
        <Tile label="Active runs" value={String(runs.filter(r=>r.status==='running').length)} />
        <Tile label="Recent fails" value={String(fail)} />
        <Tile label="Total runs" value={String(runs.length)} />
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="text-sm font-medium mb-2">Recent runs</div>
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="p-2">ID</th>
                <th className="p-2">Suite</th>
                <th className="p-2">Status</th>
                <th className="p-2">Started</th>
                <th className="p-2">Finished</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(r => (
                <tr key={r.id} className="border-t">
                  <td className="p-2">{r.id}</td>
                  <td className="p-2">{r.suite_id}</td>
                  <td className="p-2"><StatusBadge s={r.status} /></td>
                  <td className="p-2">{r.started_at?.replace('T',' ').slice(0,19) || '—'}</td>
                  <td className="p-2">{r.finished_at?.replace('T',' ').slice(0,19) || '—'}</td>
                </tr>
              ))}
              {!runs.length && (
                <tr><td className="p-4 text-gray-500" colSpan={5}>No runs yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Tile({label, value}:{label:string; value:string}) {
  return (
    <div className="bg-white rounded shadow p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  );
}

function StatusBadge({s}:{s:string}){
  const colors: Record<string,string> = { running: 'bg-blue-100 text-blue-700', pass: 'bg-green-100 text-green-700', fail: 'bg-red-100 text-red-700', aborted: 'bg-gray-100 text-gray-700' };
  return <span className={`px-2 py-0.5 rounded text-xs ${colors[s]||'bg-gray-100 text-gray-700'}`}>{s}</span>
}


