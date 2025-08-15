"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LineChart } from "@/components/charts/Line";
import { BarChart } from "@/components/charts/Bar";

export default function MetricsPage() {
  const series = useQuery({
    queryKey: ["metrics:series"],
    queryFn: async () => (await api.get("/api/v1/metrics/series", { params: { from: "-24h" } })).data,
  });

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Requests (24h)</CardTitle>
        </CardHeader>
        <CardContent>
          <LineChart data={series.data ?? []} x="timestamp" y="value" />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Errors (24h)</CardTitle>
        </CardHeader>
        <CardContent>
          <BarChart data={series.data ?? []} x="timestamp" y="value" />
        </CardContent>
      </Card>
    </div>
  );
}


