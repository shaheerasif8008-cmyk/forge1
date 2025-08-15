"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { KpiCard } from "@/components/metrics/KpiCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LineChart } from "@/components/charts/Line";
import { useEffect, useState } from "react";
import { track } from "@/lib/telemetry";

export default function DashboardPage() {
  const [firstTime, setFirstTime] = useState(false);
  useEffect(() => {
    // naive first-time flag in localStorage per tenant
    const key = "forge1_first_time";
    const seen = typeof window !== 'undefined' ? localStorage.getItem(key) : '1';
    if (!seen) {
      setFirstTime(true);
      localStorage.setItem(key, '1');
    }
    track({ type: 'clicked_x', props: { page: 'dashboard' } });
  }, []);
  const summary = useQuery({
    queryKey: ["metrics:summary"],
    queryFn: async () => {
      const res = await api.get("/api/v1/metrics/summary");
      return res.data;
    },
  });

  const series = useQuery({
    queryKey: ["metrics:series"],
    queryFn: async () => {
      const res = await api.get("/api/v1/metrics/series", { params: { from: "-7d" } });
      return res.data;
    },
  });

  type Point = { value: number } & Record<string, unknown>;
  const kpiData = (series.data as Point[] | undefined)?.map((d, i: number) => ({ x: i, y: d.value })) ?? [];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Your AI workforce at a glance</h1>

      {firstTime && (
        <div className="rounded-md border p-3 text-sm">
          <div className="font-medium">Getting started checklist</div>
          <ul className="list-disc pl-5">
            <li>Create an employee from a template in the Builder</li>
            <li>Run a task to see results and logs</li>
            <li>Review metrics here and in the Metrics page</li>
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KpiCard title="Requests" value={summary.data?.requests ?? "—"} loading={summary.isLoading} data={kpiData} />
        <KpiCard title="Errors" value={summary.data?.errors ?? "—"} loading={summary.isLoading} data={kpiData} />
        <KpiCard title="Latency (ms)" value={summary.data?.p95_ms ?? "—"} loading={summary.isLoading} data={kpiData} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Traffic</CardTitle>
        </CardHeader>
        <CardContent>
          <LineChart data={series.data ?? []} x="timestamp" y="value" />
        </CardContent>
      </Card>
    </div>
  );
}


