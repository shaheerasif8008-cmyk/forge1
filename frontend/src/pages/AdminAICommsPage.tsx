import { useEffect, useMemo, useRef, useState } from "react";
import config from "../config";
import { useSession } from "../components/SessionManager";

interface CloudEvent {
  id: string;
  source: string;
  type: string;
  time: string;
  subject?: string | null;
  datacontenttype?: string;
  data: Record<string, unknown>;
  tenant_id?: string | null;
  employee_id?: string | null;
  trace_id?: string | null;
  actor?: string | null;
  ttl?: number | null;
  version: string;
}

export default function AdminAICommsPage() {
  const { token } = useSession();
  const [events, setEvents] = useState<CloudEvent[]>([]);
  const [filterTenant, setFilterTenant] = useState("");
  const [filterEmployee, setFilterEmployee] = useState("");
  const [filterType, setFilterType] = useState("");
  const [search, setSearch] = useState("");
  const esRef = useRef<EventSource | null>(null);

  const params = useMemo(() => {
    const p = new URLSearchParams();
    if (filterTenant) p.set("tenant_id", filterTenant);
    if (filterEmployee) p.set("employee_id", filterEmployee);
    if (filterType) p.set("type", filterType);
    return p.toString();
  }, [filterTenant, filterEmployee, filterType]);

  useEffect(() => {
    if (!token) return;
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    const qp = params ? `?${params}&token=${encodeURIComponent(token || "")}` : `?token=${encodeURIComponent(token || "")}`;
    const url = `${config.apiUrl}/api/v1/admin/ai-comms/events${qp}`;
    const es = new EventSource(url, { withCredentials: false });
    esRef.current = es;
    es.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data) as CloudEvent;
        setEvents((prev) => {
          const next = [...prev, payload];
          if (next.length > 100) next.shift();
          return next;
        });
      } catch {}
    };
    es.onerror = () => {
      // auto-reconnect by replacing EventSource
      try { es.close(); } catch {}
      esRef.current = null;
      setTimeout(() => {
        if (!esRef.current) {
          // trigger effect by changing state
          setFilterType((s) => s);
        }
      }, 1000);
    };
    return () => {
      try { es.close(); } catch {}
      esRef.current = null;
    };
  }, [token, params]);

  const filtered = useMemo(() => {
    if (!search) return events.slice().reverse();
    const q = search.toLowerCase();
    return events
      .filter((e) =>
        [e.type, e.source, e.subject || "", e.tenant_id || "", e.employee_id || "", JSON.stringify(e.data)]
          .join(" ")
          .toLowerCase()
          .includes(q)
      )
      .slice()
      .reverse();
  }, [events, search]);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">AI Comms</h1>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <input className="border rounded px-3 py-2" placeholder="Filter tenant_id" value={filterTenant} onChange={(e) => setFilterTenant(e.target.value)} />
        <input className="border rounded px-3 py-2" placeholder="Filter employee_id" value={filterEmployee} onChange={(e) => setFilterEmployee(e.target.value)} />
        <input className="border rounded px-3 py-2" placeholder="Filter type" value={filterType} onChange={(e) => setFilterType(e.target.value)} />
        <input className="border rounded px-3 py-2" placeholder="Search" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>
      <div className="bg-white border rounded">
        <div className="grid grid-cols-6 gap-2 px-3 py-2 text-xs font-medium bg-gray-50 border-b">
          <div>time</div>
          <div>type</div>
          <div>source</div>
          <div>tenant</div>
          <div>employee</div>
          <div>data</div>
        </div>
        <div className="max-h-[60vh] overflow-y-auto divide-y">
          {filtered.map((e, idx) => (
            <div key={`${e.id}-${idx}`} className="grid grid-cols-6 gap-2 px-3 py-2 text-xs">
              <div title={e.time}>{new Date(e.time).toLocaleTimeString()}</div>
              <div className="font-mono text-blue-700" title={e.type}>{e.type}</div>
              <div className="truncate" title={e.source}>{e.source}</div>
              <div className="truncate" title={e.tenant_id || ""}>{e.tenant_id}</div>
              <div className="truncate" title={e.employee_id || ""}>{e.employee_id}</div>
              <div className="truncate" title={JSON.stringify(e.data)}>{JSON.stringify(e.data)}</div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="px-3 py-6 text-sm text-gray-500">No events yet…</div>
          )}
        </div>
      </div>
    </div>
  );
}


