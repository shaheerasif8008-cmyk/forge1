"use client";

import { useEffect, useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { apiClient, type TaskTrace } from "@/lib/api";

export default function TraceDialog({ taskId, onClose }: { taskId: number | null; onClose: () => void }) {
  const [trace, setTrace] = useState<TaskTrace | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!taskId) return;
    setLoading(true);
    apiClient.getTaskTrace(taskId).then(setTrace).finally(() => setLoading(false));
  }, [taskId]);
  return (
    <Dialog open={!!taskId} onClose={onClose}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-lg font-semibold">Task Trace #{taskId}</div>
        <button className="text-sm underline" onClick={onClose}>Close</button>
      </div>
      {loading ? (
        <div className="text-sm text-muted-foreground">Loading...</div>
      ) : !trace ? (
        <div className="text-sm text-muted-foreground">No trace</div>
      ) : (
        <div className="space-y-3 text-sm">
          <div>Model: {trace.model_used || "-"} · Success: {trace.success ? "yes" : "no"} · Time: {trace.execution_time ?? "-"} ms</div>
          <div>
            <div className="font-medium mb-1">Tool Calls</div>
            {!trace.tool_calls.length ? (
              <div className="text-muted-foreground">None</div>
            ) : (
              <div className="space-y-2">
                {trace.tool_calls.map((t, i) => (
                  <div key={i} className="border rounded-md p-2">
                    <div className="font-medium">{t.name}</div>
                    <div className="text-xs text-muted-foreground">{t.status || "ok"} · {t.duration_ms ?? "-"} ms</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Dialog>
  );
}


