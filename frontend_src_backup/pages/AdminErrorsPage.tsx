import { useEffect, useMemo, useState } from "react";
import { useSession } from "../components/SessionManager";
import config from "../config";

type Row = {
  id: number;
  trace_id: string | null;
  employee_id: string | null;
  prompt_preview: string | null;
  error_message: string | null;
  tokens_used: number | null;
  created_at: string | null;
  llm_trace?: any;
  tool_stack?: any;
};

export default function AdminErrorsPage() {
  const { token } = useSession();
  const [rows, setRows] = useState<Row[]>([]);
  const headers = useMemo(() => ({ ...(token ? { Authorization: `Bearer ${token}` } : {}) }), [token]);

  useEffect(() => {
    (async () => {
      const r = await fetch(`${config.apiUrl}/api/v1/admin/errors?limit=50`, { headers });
      if (r.ok) setRows(await r.json());
    })();
  }, [headers]);

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Error Inspector</h1>
      <div className="bg-white rounded shadow p-4">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-600">
                <th className="p-2">Time</th>
                <th className="p-2">Trace</th>
                <th className="p-2">Employee</th>
                <th className="p-2">Preview</th>
                <th className="p-2">Error</th>
                <th className="p-2">Tokens</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t">
                  <td className="p-2">{r.created_at ? new Date(r.created_at).toLocaleString() : "-"}</td>
                  <td className="p-2 font-mono text-xs">{r.trace_id || "-"}</td>
                  <td className="p-2">{r.employee_id || "-"}</td>
                  <td className="p-2">{r.prompt_preview || "-"}</td>
                  <td className="p-2 text-red-700">{r.error_message || "-"}</td>
                  <td className="p-2">{r.tokens_used ?? "-"}</td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td colSpan={6} className="p-3 text-gray-500">
                    No errors yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}


