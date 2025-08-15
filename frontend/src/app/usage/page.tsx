"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function UsagePage() {
  const { data, isLoading } = useQuery({ queryKey: ["metrics-summary-usage"], queryFn: () => apiClient.getClientMetricsSummary(720) });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Usage & Billing</h1>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>Summary (30d)</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Metric label="Tasks" value={String(data?.tasks ?? 0)} />
              <Metric label="Tokens" value={String(data?.tokens ?? 0)} />
              <Metric label="Avg Latency" value={`${Math.round(data?.avg_duration_ms || 0)} ms`} />
              <Metric label="Est. Spend" value={`$${(((data?.cost_cents || 0) / 100)).toFixed(2)}`} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border p-4">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  );
}
