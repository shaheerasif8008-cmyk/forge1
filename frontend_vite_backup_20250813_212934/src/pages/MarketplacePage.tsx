import { useEffect, useMemo, useState } from "react";
import config from "../config";
import { useSession } from "../components/SessionManager";
import { LoadingSpinner } from "../components/LoadingSpinner";

interface TemplateOut {
  key: string;
  name: string;
  vertical: string | null;
  description: string;
  required_tools: string[];
  version: string;
}

export default function MarketplacePage() {
  const { token } = useSession();
  const [templates, setTemplates] = useState<TemplateOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [vertical, setVertical] = useState("");
  const [deployingKey, setDeployingKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (vertical) qs.set("vertical", vertical);
      if (search) qs.set("search", search);
      const res = await fetch(`${config.apiUrl}/api/v1/marketplace/templates?${qs.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = (await res.json()) as TemplateOut[];
      setTemplates(data);
    } catch (e) {
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [token]);

  const filtered = useMemo(() => {
    return templates;
  }, [templates]);

  const deploy = async (key: string) => {
    setDeployingKey(key);
    setMessage(null);
    try {
      const res = await fetch(`${config.apiUrl}/api/v1/marketplace/templates/${encodeURIComponent(key)}/deploy`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(`Deployed ${data.name} (id: ${data.employee_id})`);
      } else {
        setMessage(data.detail || 'Deploy failed');
      }
    } catch (e) {
      setMessage('Deploy failed');
    } finally {
      setDeployingKey(null);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">AI Employee Marketplace</h1>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <input className="border rounded px-3 py-2" placeholder="Search" value={search} onChange={(e) => setSearch(e.target.value)} />
        <input className="border rounded px-3 py-2" placeholder="Vertical (e.g., sales, support)" value={vertical} onChange={(e) => setVertical(e.target.value)} />
        <button className="px-3 py-2 bg-blue-600 text-white rounded" onClick={() => void load()}>Search</button>
        {message && <div className="text-sm text-green-700">{message}</div>}
      </div>
      {loading ? (
        <div className="py-12"><LoadingSpinner text="Loading templates..." /></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map(t => (
            <div key={t.key} className="bg-white border rounded p-4 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <div className="text-lg font-medium">{t.name}</div>
                {t.vertical && <span className="text-xs bg-gray-100 border px-2 py-0.5 rounded">{t.vertical}</span>}
              </div>
              <div className="text-sm text-gray-700">{t.description}</div>
              <div className="text-xs text-gray-500">Tools: {t.required_tools.join(', ') || 'None'}</div>
              <div className="mt-2">
                <button disabled={deployingKey===t.key} onClick={() => void deploy(t.key)} className="px-3 py-2 bg-emerald-600 text-white rounded disabled:opacity-50">
                  {deployingKey===t.key ? 'Deploying...' : 'Deploy'}
                </button>
              </div>
            </div>
          ))}
          {!filtered.length && <div className="text-sm text-gray-500">No templates found.</div>}
        </div>
      )}
    </div>
  );
}


