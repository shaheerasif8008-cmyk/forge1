"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth";
import { apiClient } from "@/lib/api";
import { useMemo } from "react";
import { useSSE } from "@/hooks/useSSE";

interface CloudEventPayload {
  type?: string;
  source?: string;
  tenant_id?: string;
  employee_id?: string;
  data?: unknown;
  trace_id?: string;
}

export default function OperationsPage() {
  const { token } = useAuth();
  const url = useMemo(() => apiClient.buildEventsUrl({}, token), [token]);
  const { data, isConnected, error } = useSSE<CloudEventPayload>({ url, enabled: !!token });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Operations</h1>
      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>Live Events</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between text-sm mb-3">
            <div>Status: {isConnected ? <span className="text-success">connected</span> : <span className="text-warning">connecting...</span>}</div>
            {error && <div className="text-danger">{error}</div>}
          </div>
          {!data.length ? (
            <div className="text-sm text-muted-foreground">No events yet. Trigger runs to see activity.</div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-auto">
              {data.map((ev, idx) => (
                <div key={idx} className="border rounded-md p-2 text-xs">
                  <div className="font-medium">{ev.type || "event"}</div>
                  <div className="text-muted-foreground">{ev.employee_id || "-"} · {ev.trace_id || "-"}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
