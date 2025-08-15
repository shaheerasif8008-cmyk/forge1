"use client";

import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient, type EmployeeOut } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useState } from "react";
import toast from "react-hot-toast";

export default function EmployeeDetailPage() {
  const params = useParams<{ id: string }>();
  const employeeId = params?.id as string;
  const qc = useQueryClient();
  const [task, setTask] = useState("");

  const { data: emp, isLoading } = useQuery({
    queryKey: ["employee", employeeId],
    queryFn: () => apiClient.getEmployee(employeeId),
  });

  const { data: logs, isLoading: loadingLogs } = useQuery({
    queryKey: ["employee-logs", employeeId],
    queryFn: () => apiClient.getEmployeeLogs(employeeId, 20, 0),
    refetchInterval: 5000,
  });

  const { data: perf } = useQuery({
    queryKey: ["employee-perf", employeeId],
    queryFn: () => apiClient.getEmployeePerformance(employeeId),
  });

  const runMutation = useMutation({
    mutationFn: async () => apiClient.runEmployee(employeeId, { task, iterations: 1, context: {} }),
    onSuccess: (res) => {
      toast.success("Run started");
      setTask("");
      qc.invalidateQueries({ queryKey: ["employee-logs", employeeId] });
    },
    onError: () => toast.error("Run failed"),
  });

  return (
    <div className="p-6 space-y-6">
      {isLoading ? (
        <Skeleton className="h-8 w-64" />
      ) : (
        <h1 className="text-2xl font-semibold">{(emp as EmployeeOut | undefined)?.name || "Employee"}</h1>
      )}

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>Run Task</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input placeholder="Describe the task" value={task} onChange={(e) => setTask(e.target.value)} />
            <Button onClick={() => runMutation.mutate()} disabled={!task || runMutation.isPending}>Run</Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 shadow-card">
          <CardHeader>
            <CardTitle>Recent Logs</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingLogs ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : !logs?.length ? (
              <div className="text-sm text-muted-foreground">No logs yet</div>
            ) : (
              <div className="space-y-2">
                {logs.map((l) => (
                  <div key={l.id} className="flex items-center justify-between border rounded-md p-3">
                    <div className="text-sm">
                      <div className="font-medium">{l.task_type}</div>
                      <div className="text-xs text-muted-foreground">{l.created_at}</div>
                    </div>
                    <div className="text-xs">
                      {l.success ? <span className="text-success">OK</span> : <span className="text-danger">ERR</span>} · {l.execution_time ?? "—"} ms
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div>Tasks: {perf?.tasks ?? 0}</div>
              <div>Errors: {perf?.errors ?? 0}</div>
              <div>Success: {typeof perf?.success_ratio === "number" ? `${Math.round((perf.success_ratio || 0) * 100)}%` : "—"}</div>
              <div>Avg Latency: {perf?.avg_duration_ms ? `${Math.round(perf.avg_duration_ms)} ms` : "—"}</div>
              <div>Tool Calls: {perf?.tool_calls ?? 0}</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
