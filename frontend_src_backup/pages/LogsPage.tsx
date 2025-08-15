import { useEffect, useState } from "react";
import config from "../config";

type Log = {
  id: number;
  task_type: string;
  model_used?: string;
  success: boolean;
  execution_time?: number;
  error_message?: string;
  created_at?: string;
};

export default function LogsPage() {
  const [employeeId, setEmployeeId] = useState("");
  const [logs, setLogs] = useState<Log[]>([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);

  const loadLogs = async () => {
    const token = localStorage.getItem("access_token");
    if (!token || !employeeId) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${config.apiUrl}/api/v1/employees/${employeeId}/logs?limit=20&offset=${page * 20}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (res.ok) {
        const data = (await res.json()) as Log[];
        setLogs(data);
      } else {
        setLogs([]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!employeeId) return;
    void loadLogs();
    const id = setInterval(loadLogs, 5000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeeId, page]);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Employee Logs</h1>
      <div className="bg-white rounded shadow p-4 flex items-center gap-3">
        <input
          value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
          placeholder="Employee ID"
          className="border rounded px-3 py-2 flex-1"
        />
        <button
          onClick={loadLogs}
          className="bg-blue-600 text-white px-4 py-2 rounded"
          disabled={!employeeId || loading}
        >
          {loading ? "Loading..." : "Load"}
        </button>
      </div>
      <div className="bg-white rounded shadow p-4">
        {logs.length ? (
          <ul className="divide-y">
            {logs.map((l) => (
              <li key={l.id} className="py-2 text-sm">
                <div className="flex justify-between">
                  <div>
                    <div className="font-medium">{l.task_type}</div>
                    <div className="text-gray-500">{l.model_used}</div>
                  </div>
                  <div className="text-right">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${l.success ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}
                    >
                      {l.success ? "Success" : "Failed"}
                    </span>
                    {l.execution_time !== undefined && (
                      <div className="text-gray-500">{l.execution_time} ms</div>
                    )}
                    {l.created_at && (
                      <div className="text-gray-400 text-xs">{l.created_at}</div>
                    )}
                  </div>
                </div>
                {l.error_message && (
                  <div className="text-red-700 mt-1">{l.error_message}</div>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-600 text-sm">No logs</p>
        )}
        <div className="flex justify-end gap-2 mt-3">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            className="px-3 py-1 border rounded"
            disabled={page === 0}
          >
            Prev
          </button>
          <button onClick={() => setPage((p) => p + 1)} className="px-3 py-1 border rounded">
            Next
          </button>
        </div>
      </div>
    </div>
  );
}


