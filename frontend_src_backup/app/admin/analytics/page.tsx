"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Row = { name: string; count: number };

export default function AdminAnalyticsPage() {
  const templates = useQuery({
    queryKey: ["admin:templates"],
    queryFn: async () => (await api.get<Row[]>("/api/v1/metrics/top/templates")).data,
  });
  const tools = useQuery({
    queryKey: ["admin:tools"],
    queryFn: async () => (await api.get<Row[]>("/api/v1/metrics/top/tools")).data,
  });
  const funnel = useQuery({
    queryKey: ["admin:funnel"],
    queryFn: async () => (await api.get<{ created: number; ran: number }>("/api/v1/metrics/funnel")).data,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Analytics</h1>
      <div>
        <div className="font-medium">Top Templates</div>
        <ul className="list-disc pl-5">
          {(templates.data || []).map((r) => (
            <li key={r.name}>{r.name}: {r.count}</li>
          ))}
        </ul>
      </div>
      <div>
        <div className="font-medium">Top Tools</div>
        <ul className="list-disc pl-5">
          {(tools.data || []).map((r) => (
            <li key={r.name}>{r.name}: {r.count}</li>
          ))}
        </ul>
      </div>
      <div>
        <div className="font-medium">Create → Run Conversion</div>
        <div>{funnel.data ? Math.round((funnel.data.ran / Math.max(1, funnel.data.created)) * 100) : 0}%</div>
      </div>
    </div>
  );
}


