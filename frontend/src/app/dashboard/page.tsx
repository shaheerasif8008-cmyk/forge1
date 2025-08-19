"use client";

import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const { data: summary, isLoading: loadingSummary, error: summaryErr, refetch } = useQuery({
    queryKey: ["metrics-summary"],
    queryFn: () => apiClient.getClientMetricsSummary(168),
    enabled: !loading,
  });
  const { data: active, isLoading: loadingActive } = useQuery({
    queryKey: ["active-employees"],
    queryFn: () => apiClient.getActiveEmployees(5),
    enabled: !loading,
    refetchInterval: 60000,
  });

  if (loading) {
    return <DashboardSkeleton />;
  }

  const kpi = summary ? [
    { title: "Active Employees", value: typeof active?.active_employees === "number" ? String(active.active_employees) : "—" },
    { title: "Tasks (7d)", value: String(summary.tasks ?? "—") },
    { title: "p95 Latency", value: summary.avg_duration_ms ? `${Math.round(summary.avg_duration_ms)} ms` : "—" },
    { title: "Success Ratio", value: summary.success_ratio ? `${Math.round(summary.success_ratio * 100)}%` : "—" },
    { title: "Tokens (7d)", value: String(summary.tokens ?? "—") },
    { title: "Est. Spend", value: typeof summary.cost_cents === "number" ? `$${(summary.cost_cents/100).toFixed(2)}` : "—" },
  ] : [
    { title: "Active Employees", value: "—" },
    { title: "Tasks (7d)", value: "—" },
    { title: "p95 Latency", value: "—" },
    { title: "Success Ratio", value: "—" },
    { title: "Tokens (7d)", value: "—" },
    { title: "Est. Spend", value: "—" },
  ];

  const chartData = (summary?.by_day || []).slice().reverse();

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 data-testid="dashboard-title" className="text-3xl font-semibold">
            Your AI workforce at a glance
          </h1>
          <p className="text-muted-foreground" data-testid="dashboard-welcome">
            Welcome back, {user?.email || "User"}
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4" data-testid="kpi-cards">
        {kpi.map((x) => (
          <KPICard key={x.title} title={x.title} value={x.value} loading={loadingSummary || loadingActive} />
        ))}
      </div>

      {/* Charts and Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 shadow-card" data-testid="chart-card">
          <CardHeader>
            <CardTitle>7-Day Trends</CardTitle>
            <CardDescription>Tokens and latency over time</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64" data-testid="chart-traffic">
              {loadingSummary ? (
                <div className="h-full flex items-center justify-center text-muted-foreground">Loading metrics...</div>
              ) : summaryErr ? (
                <div className="space-y-2">
                  <Alert variant="destructive">Failed to load metrics. <button className="underline" onClick={() => refetch()}>Retry</button></Alert>
                </div>
              ) : chartData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" hide />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Line yAxisId="left" type="monotone" dataKey="tokens" stroke="#8B5CF6" dot={false} name="Tokens" />
                    <Line yAxisId="right" type="monotone" dataKey="avg_duration_ms" stroke="#3B82F6" dot={false} name="Latency (ms)" />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">No data</div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-card" data-testid="activity-feed">
          <CardHeader>
            <CardTitle>Activity Feed</CardTitle>
            <CardDescription>Last 20 events</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="text-sm text-muted-foreground">
                No recent activity
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function KPICard({ title, value, loading }: { title: string; value: string; loading?: boolean }) {
  return (
    <Card className="shadow-card" data-testid={`kpi-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
      <CardContent className="p-4">
        <div className="text-sm font-medium text-muted-foreground">{title}</div>
        <div className="text-2xl font-semibold mt-1">{loading ? <Skeleton className="h-6 w-16" /> : value}</div>
      </CardContent>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6" data-testid="dashboard-skeleton">
      <div className="space-y-2">
        <Skeleton className="h-8 w-96" />
        <Skeleton className="h-4 w-64" />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="shadow-card">
            <CardContent className="p-4">
              <Skeleton className="h-4 w-20 mb-2" />
              <Skeleton className="h-6 w-12" />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 shadow-card">
          <CardContent className="p-6">
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
        <Card className="shadow-card">
          <CardContent className="p-6">
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}