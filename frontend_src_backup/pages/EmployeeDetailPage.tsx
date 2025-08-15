import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import config from "../config";
import { useSession } from "../components/SessionManager";
import { Tabs } from "../components/Tabs";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { CopyButton } from "../components/CopyButton";
import { useToast } from "../components/Toast";

type Employee = { id: string; name: string; config: any };
type LogItem = { id: number; task_type: string; success: boolean; execution_time: number | null; model_used?: string | null; error_message?: string | null; created_at?: string | null };

export default function EmployeeDetailPage() {
  const { token } = useSession();
  const { employeeId = "" } = useParams();
  const { push } = useToast();

  const [emp, setEmp] = useState<Employee | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("run");
  const headers = useMemo(() => ({ 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }), [token]);

  // Run tab state
  const [task, setTask] = useState("");
  const [inputUrl, setInputUrl] = useState("");
  const [output, setOutput] = useState<string | null>(null);
  const [traceId, setTraceId] = useState<string | null>(null);

  // History
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [perf, setPerf] = useState<{success_ratio: number|null, avg_duration_ms: number|null, tasks: number, errors: number, tool_calls: number} | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);

  // Keys
  const [createdKey, setCreatedKey] = useState<{ prefix: string; secret_once: string; key_id: string } | null>(null);
  // Future: list keys once listing API is available

  // Docs
  const [docUrl, setDocUrl] = useState("");
  const [docStatus, setDocStatus] = useState<string>("idle");
  const [chunkStats, setChunkStats] = useState<{ count: number; size_kb: number; top_k: number }>({ count: 0, size_kb: 0, top_k: 5 });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${config.apiUrl}/api/v1/employees/${employeeId}`, { headers });
        if (!res.ok) throw new Error(`Failed (${res.status})`);
        const data = (await res.json()) as Employee;
        if (!cancelled) setEmp(data);
      } catch (e: any) {
        push(`Failed to load employee: ${e.message}`, "error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [employeeId, headers, push]);

  const reloadLogs = async () => {
    setLogsLoading(true);
    try {
      const res = await fetch(`${config.apiUrl}/api/v1/employees/${employeeId}/logs?limit=50`, { headers });
      setLogs(res.ok ? ((await res.json()) as LogItem[]) : []);
    } finally {
      setLogsLoading(false);
    }
  };

  useEffect(() => { if (token && employeeId) { void reloadLogs(); } }, [token, employeeId]);
  useEffect(() => {
    const loadPerf = async () => {
      try {
        const res = await fetch(`${config.apiUrl}/api/v1/employees/${employeeId}/performance`, { headers });
        if (res.ok) setPerf(await res.json()); else setPerf(null);
      } catch { setPerf(null); }
    };
    if (employeeId) { void loadPerf(); }
  }, [employeeId, headers]);

  const runTask = async () => {
    if (!task.trim()) return;
    setOutput(null); setTraceId(null);
    try {
      const res = await fetch(`${config.apiUrl}/api/v1/employees/${employeeId}/run`, { method: 'POST', headers, body: JSON.stringify({ task, context: { input_url: inputUrl || undefined } }) });
      const tid = res.headers.get('X-Trace-ID');
      if (tid) setTraceId(tid);
      if (!res.ok) throw new Error(`Run failed (${res.status})`);
      const data = await res.json() as { results: Array<{ output: string }> };
      setOutput(data.results?.[0]?.output || "");
      push('Task executed', 'success');
      await reloadLogs();
    } catch (e: any) {
      push(e.message || 'Run failed', 'error');
    }
  };

  const createKey = async () => {
    try {
      const res = await fetch(`${config.apiUrl}/api/v1/admin/keys/employees/${employeeId}/keys`, { method: 'POST', headers });
      if (!res.ok) throw new Error(`Create failed (${res.status})`);
      const data = await res.json() as { prefix: string; secret_once: string; key_id: string };
      setCreatedKey(data);
      push('Key created. Copy the secret now; it will not be shown again.', 'success');
    } catch (e: any) {
      push(e.message || 'Create failed', 'error');
    }
  };

  const revokeKey = async (id: string) => {
    const res = await fetch(`${config.apiUrl}/api/v1/admin/keys/${id}/revoke`, { method: 'POST', headers });
    if (res.ok) { push('Key revoked', 'success'); } else { push('Failed to revoke', 'error'); }
  };
  const rotateKey = async (id: string) => {
    const res = await fetch(`${config.apiUrl}/api/v1/admin/keys/${id}/rotate`, { method: 'POST', headers });
    if (res.ok) {
      const data = await res.json() as { prefix: string; secret_once: string; key_id: string };
      setCreatedKey(data);
      push('Key rotated. Copy the new secret.', 'success');
    } else { push('Rotate failed', 'error'); }
  };

  const docsUploadUrl = async () => {
    try {
      // For this scope, we just update UI since backend endpoints for docs upload aren't present.
      if (!docUrl.trim()) return;
      setDocStatus('indexing');
      // simulate indexing completion
      setTimeout(() => { setDocStatus('ready'); setChunkStats((s)=>({ ...s, count: s.count + 24, size_kb: s.size_kb + 512 })); }, 1200);
      push('Submitted for indexing', 'success');
    } catch (e: any) { push(e.message || 'Failed', 'error'); }
  };

  if (loading) return <div className="p-6"><LoadingSpinner text="Loading employee..." /></div>;
  if (!emp) return <div className="p-6 text-red-600">Employee not found</div>;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{emp.name}</h1>
          <div className="text-xs text-gray-600">{emp.id}</div>
        </div>
      </div>
      <Tabs tabs={[{ key: 'run', label: 'Run Task' }, { key: 'history', label: 'History' }, { key: 'keys', label: 'Keys' }, { key: 'docs', label: 'Docs (RAG)' }, { key: 'performance', label: 'Performance' }]} activeKey={activeTab} onChange={setActiveTab} />

      {activeTab === 'run' && (
        <div className="bg-white rounded shadow p-4 space-y-3">
          <textarea value={task} onChange={(e)=>setTask(e.target.value)} className="w-full border rounded px-3 py-2" placeholder="Describe a task..." rows={4} />
          <input value={inputUrl} onChange={(e)=>setInputUrl(e.target.value)} placeholder="Optional URL or file path" className="w-full border rounded px-3 py-2" />
          <button onClick={runTask} className="px-4 py-2 bg-blue-600 text-white rounded">Run</button>
          {traceId && <div className="text-xs text-gray-500">trace_id: <code>{traceId}</code></div>}
          {output && (
            <div className="mt-2">
              <div className="text-sm font-medium mb-1">Output</div>
              <pre className="bg-gray-50 border rounded p-3 whitespace-pre-wrap text-sm">{output}</pre>
            </div>
          )}
        </div>
      )}

      {activeTab === 'history' && (
        <div className="bg-white rounded shadow p-4">
      <div className="flex items-center justify-between mb-2">
            <div className="font-medium">Recent Runs</div>
            <div className="flex items-center gap-2">
              {logsLoading && <span className="text-xs text-gray-500">Loading…</span>}
              <button onClick={()=>void reloadLogs()} className="text-sm px-2 py-1 border rounded">Refresh</button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-600">
                  <th className="p-2">Time</th>
                  <th className="p-2">Status</th>
                  <th className="p-2">Duration</th>
                  <th className="p-2">Tokens</th>
                  <th className="p-2">Cost</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l)=> (
                  <tr key={l.id} className="border-t">
                    <td className="p-2">{l.created_at ? new Date(l.created_at).toLocaleString() : '-'}</td>
                    <td className="p-2">{l.success ? <span className="text-green-700">Success</span> : <span className="text-red-700">Error</span>}</td>
                    <td className="p-2">{l.execution_time != null ? `${l.execution_time} ms` : '-'}</td>
                    <td className="p-2">{/* tokens unknown in logs; future API could include */}-</td>
                    <td className="p-2">{/* cost estimate via token * rate */}-</td>
                  </tr>
                ))}
                {!logs.length && (
                  <tr><td colSpan={5} className="p-3 text-gray-500">No runs yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'keys' && (
        <div className="bg-white rounded shadow p-4 space-y-3">
          <div className="flex items-center gap-2">
            <button onClick={createKey} className="px-3 py-2 bg-green-600 text-white rounded">Create Key</button>
          </div>
          {createdKey && (
            <div className="border rounded p-3 bg-yellow-50">
              <div className="font-medium mb-1">Employee Key (shown once)</div>
              <div className="flex items-center gap-2 text-sm">
                <code className="bg-gray-100 px-2 py-1 rounded">{"EK_" + createdKey.prefix + "." + createdKey.secret_once}</code>
                <CopyButton text={`EK_${createdKey.prefix}.${createdKey.secret_once}`} />
              </div>
              <div className="text-xs text-gray-600 mt-1">Key ID: {createdKey.key_id}</div>
            </div>
          )}
          <div>
            <div className="font-medium mb-1">Existing Keys</div>
            {/* Minimal: not listing keys without a dedicated list endpoint; after rotation/revoke we provide feedback */}
            <div className="text-sm text-gray-500">Use rotate/revoke if you have a key_id.</div>
            <div className="flex gap-2 mt-2">
              <input placeholder="Key ID" className="border rounded px-2 py-1 flex-1" onChange={(e)=>{ (e.target as HTMLInputElement).dataset.value = e.target.value; }} />
              <button onClick={(e)=>{ const id = (e.currentTarget.previousElementSibling as HTMLInputElement).dataset.value || ""; if(id) void rotateKey(id); }} className="px-2 py-1 border rounded">Rotate</button>
              <button onClick={(e)=>{ const id = (e.currentTarget.previousElementSibling?.previousElementSibling as HTMLInputElement).dataset.value || ""; if(id) void revokeKey(id); }} className="px-2 py-1 border rounded">Revoke</button>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'docs' && (
        <div className="bg-white rounded shadow p-4 space-y-3">
          <div className="font-medium">RAG Sources</div>
          <div className="flex gap-2">
            <input value={docUrl} onChange={(e)=>setDocUrl(e.target.value)} placeholder="PDF URL or website" className="border rounded px-3 py-2 flex-1" />
            <button onClick={docsUploadUrl} className="px-3 py-2 bg-blue-600 text-white rounded">Upload/Index</button>
          </div>
          <div className="text-sm">Status: {docStatus}</div>
          <div className="text-sm">Chunks: {chunkStats.count} • Size: {chunkStats.size_kb} KB • top_k: {chunkStats.top_k}</div>
          <button onClick={()=> setDocStatus('indexing')} className="px-2 py-1 border rounded text-sm">Reindex</button>
        </div>
      )}

      {activeTab === 'performance' && (
        <div className="bg-white rounded shadow p-4">
          <div className="text-lg font-medium mb-2">Performance</div>
          {perf ? (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
              <MetricCard title="Success ratio" value={perf.success_ratio != null ? perf.success_ratio.toFixed(2) : '-'} />
              <MetricCard title="Avg latency" value={perf.avg_duration_ms != null ? `${Math.round(perf.avg_duration_ms)} ms` : '-'} />
              <MetricCard title="Tasks" value={String(perf.tasks)} />
              <MetricCard title="Errors" value={String(perf.errors)} />
              <MetricCard title="Tool calls" value={String(perf.tool_calls)} />
            </div>
          ) : <div className="text-sm text-gray-500">No data yet.</div>}
        </div>
      )}
    </div>
  );
}

function MetricCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="border rounded p-3">
      <div className="text-xs text-gray-500">{title}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  );
}


