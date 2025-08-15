import { useEffect, useState } from "react";
import config from "../config";

type Health = { status: string; postgres?: boolean; redis?: boolean };

export default function HealthPage() {
  const [live, setLive] = useState<string>("unknown");
  const [ready, setReady] = useState<Health | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchOnce = async () => {
      try {
        const r1 = await fetch(`${config.apiUrl}/api/v1/health/live`);
        if (!mounted) return;
        setLive(r1.ok ? (await r1.json()).status : "unknown");

        const r2 = await fetch(`${config.apiUrl}/api/v1/health/ready`);
        if (!mounted) return;
        setReady(r2.ok ? ((await r2.json()) as Health) : null);
      } catch {
        if (!mounted) return;
        setLive("unknown");
        setReady(null);
      }
    };
    fetchOnce();
    const id = setInterval(fetchOnce, 10000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Backend Health</h1>
      <div className="bg-white rounded shadow p-6">
        <div className="space-y-3 text-sm">
          <div className="flex items-center">
            <span className="font-medium w-28">Live:</span>
            <span className={`px-2 py-0.5 rounded text-xs ${live === "live" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-700"}`}>{live}</span>
          </div>
          <div className="flex items-center">
            <span className="font-medium w-28">Ready:</span>
            <span className={`px-2 py-0.5 rounded text-xs ${ready?.status === "ready" || ready?.status === "ready" || ready?.status === "ready" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}`}>{ready?.status ?? "unknown"}</span>
          </div>
          {ready && (
            <>
              <div className="flex items-center">
                <span className="font-medium w-28">Postgres:</span>
                <span className={`px-2 py-0.5 rounded text-xs ${ready.postgres ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>{String(ready.postgres)}</span>
              </div>
              <div className="flex items-center">
                <span className="font-medium w-28">Redis:</span>
                <span className={`px-2 py-0.5 rounded text-xs ${ready.redis ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>{String(ready.redis)}</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}


