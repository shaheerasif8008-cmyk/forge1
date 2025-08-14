import { useEffect, useMemo, useState } from "react";
import { useSession } from "../components/SessionManager";
import config from "../config";

type Flag = { tenant_id: string; flag: string; enabled: boolean; updated_at: string };

export default function AdminFeatureFlagsPage() {
  const { token, user } = useSession();
  const [flags, setFlags] = useState<Flag[]>([]);
  const [newFlag, setNewFlag] = useState("");
  const headers = useMemo(() => ({ "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) }), [token]);

  const load = async () => {
    if (!user?.tenant_id) return;
    const r = await fetch(`${config.apiUrl}/api/v1/admin/flags/list?tenant_id=${encodeURIComponent(user.tenant_id)}`, { headers });
    if (r.ok) setFlags(await r.json());
  };

  useEffect(() => { void load(); }, [token]);

  const toggle = async (flag: string, enabled: boolean) => {
    if (!user?.tenant_id) return;
    await fetch(`${config.apiUrl}/api/v1/admin/flags/set`, { method: "POST", headers, body: JSON.stringify({ tenant_id: user.tenant_id, flag, enabled }) });
    void load();
  };

  const add = async () => {
    if (!newFlag.trim() || !user?.tenant_id) return;
    await fetch(`${config.apiUrl}/api/v1/admin/flags/set`, { method: "POST", headers, body: JSON.stringify({ tenant_id: user.tenant_id, flag: newFlag.trim(), enabled: true }) });
    setNewFlag("");
    void load();
  };

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Feature Flags</h1>
      <div className="bg-white rounded shadow p-4 space-y-3">
        <div className="flex gap-2">
          <input className="border rounded px-3 py-2 flex-1" placeholder="feature.flag" value={newFlag} onChange={(e) => setNewFlag(e.target.value)} />
          <button onClick={add} className="px-3 py-2 bg-blue-600 text-white rounded">Add</button>
        </div>
        <div className="divide-y">
          {flags.map((f) => (
            <div key={f.flag} className="flex items-center justify-between py-2">
              <div>
                <div className="font-medium text-sm">{f.flag}</div>
                <div className="text-xs text-gray-500">updated {new Date(f.updated_at).toLocaleString()}</div>
              </div>
              <button onClick={() => void toggle(f.flag, !f.enabled)} className={`px-3 py-1 rounded text-sm ${f.enabled ? "bg-green-600 text-white" : "bg-gray-200"}`}>{f.enabled ? "On" : "Off"}</button>
            </div>
          ))}
          {!flags.length && <div className="text-sm text-gray-500 py-2">No flags yet</div>}
        </div>
      </div>
    </div>
  );
}


