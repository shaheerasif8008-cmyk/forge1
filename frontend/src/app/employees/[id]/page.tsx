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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import ToolToggles from "./ToolToggles";
import TraceDialog from "./TraceDialog";

export default function EmployeeDetailPage() {
  const params = useParams<{ id: string }>();
  const employeeId = params?.id as string;
  const qc = useQueryClient();
  const [task, setTask] = useState("");
  const [memQuery, setMemQuery] = useState("");
  const [memContent, setMemContent] = useState("");
  const [traceTaskId, setTraceTaskId] = useState<number | null>(null);

  const { data: emp, isLoading, error: empError } = useQuery({
    queryKey: ["employee", employeeId],
    queryFn: () => apiClient.getEmployee(employeeId),
  });

  const { data: logs, isLoading: loadingLogs, error: logsError } = useQuery({
    queryKey: ["employee-logs", employeeId],
    queryFn: () => apiClient.getEmployeeLogs(employeeId, 20, 0),
    refetchInterval: 5000,
  });

  const { data: perf, error: perfError } = useQuery({
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

  const addMemMutation = useMutation({
    mutationFn: async () => apiClient.addEmployeeMemory(employeeId, memContent, "note"),
    onSuccess: () => {
      toast.success("Memory added");
      setMemContent("");
      qc.invalidateQueries({ queryKey: ["employee-memory", employeeId, memQuery] });
    },
    onError: () => toast.error("Add memory failed"),
  });

  const { data: memResults, isLoading: loadingMem, error: memError } = useQuery({
    queryKey: ["employee-memory", employeeId, memQuery],
    queryFn: () => apiClient.searchEmployeeMemory(employeeId, memQuery || "", memQuery ? 10 : 50),
    enabled: !!employeeId,
  });

  return (
    <div className="p-6 space-y-6">
      {isLoading ? (
        <Skeleton className="h-8 w-64" />
      ) : empError ? (
        <div className="text-sm text-red-600">Failed to load employee.</div>
      ) : (
        <h1 className="text-2xl font-semibold" data-testid="employee-title">{(emp as EmployeeOut | undefined)?.name || "Employee"}</h1>
      )}

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>Run Task</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input data-testid="task-input" placeholder="Describe the task" value={task} onChange={(e) => setTask(e.target.value)} />
            <Button data-testid="task-run" onClick={() => runMutation.mutate()} disabled={!task || runMutation.isPending}>Run</Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="logs" className="w-full">
        <TabsList>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="memory">Memory</TabsTrigger>
          <TabsTrigger value="perf">Performance</TabsTrigger>
          <TabsTrigger value="tools">Tools</TabsTrigger>
        </TabsList>
        <TabsContent value="logs">
          <div className="grid grid-cols-1 lg:grid-cols-1 gap-6">
            <Card className="shadow-card">
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
                ) : logsError ? (
                  <div className="text-sm text-red-600">Failed to load logs.</div>
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
                        <div className="text-xs flex items-center gap-3">
                          {l.success ? <span className="text-success">OK</span> : <span className="text-danger">ERR</span>} · {l.execution_time ?? "—"} ms
                          <button className="underline" onClick={() => setTraceTaskId(l.id)} data-testid="trace-link">View Trace</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        <TabsContent value="memory">
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>Memory</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 mb-4">
                <Input data-testid="memory-search" placeholder="Search memory (q)" value={memQuery} onChange={(e) => setMemQuery(e.target.value)} />
                <Button data-testid="memory-search-btn" onClick={() => qc.invalidateQueries({ queryKey: ["employee-memory", employeeId, memQuery] })} disabled={!memQuery}>Search</Button>
              </div>
              <div className="flex gap-2 mb-4">
                <Input data-testid="memory-add" placeholder="Add memory content" value={memContent} onChange={(e) => setMemContent(e.target.value)} />
                <Button data-testid="memory-add-btn" onClick={() => addMemMutation.mutate()} disabled={!memContent || addMemMutation.isPending}>Add</Button>
              </div>
              {loadingMem ? (
                <div>Loading...</div>
              ) : memError ? (
                <div className="text-sm text-red-600">Failed to load memory.</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm font-medium mb-2">Facts</div>
                    <div className="space-y-2">
                      {(memResults?.facts || []).map((f) => (
                        <div key={`f-${f.id}`} className="border rounded-md p-3 text-sm">
                          <div className="font-medium">{f.fact}</div>
                          <div className="text-xs text-muted-foreground">score: {f.score.toFixed(3)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-medium mb-2">Events</div>
                    <div className="space-y-2">
                      {(memResults?.events || []).map((ev) => (
                        <div key={`e-${ev.id}`} className="border rounded-md p-3 text-sm">
                          <div className="font-medium">[{ev.kind}]</div>
                          <div className="whitespace-pre-wrap">{ev.content}</div>
                          <div className="text-xs text-muted-foreground">score: {ev.score.toFixed(3)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="perf">
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
        </TabsContent>
        <TabsContent value="tools">
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>Tools</CardTitle>
            </CardHeader>
            <CardContent>
              <ToolToggles employeeId={employeeId} emp={emp as EmployeeOut | undefined} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <TraceDialog taskId={traceTaskId} onClose={() => setTraceTaskId(null)} />
    </div>
  );
}
