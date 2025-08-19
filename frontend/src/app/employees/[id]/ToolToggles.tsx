"use client";

import { useMemo, useState } from "react";
import { apiClient, type EmployeeOut } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export default function ToolToggles({ employeeId, emp }: { employeeId: string; emp?: EmployeeOut }) {
  const qc = useQueryClient();
  const existing = useMemo(() => (Array.isArray(emp?.config?.tools) ? (emp?.config?.tools as any[]) : []), [emp]);
  const [tools, setTools] = useState<any[]>(existing);
  const knownTools = ["api_caller", "web_scraper", "slack_notifier", "email_dev"];
  const mu = useMutation({
    mutationFn: async (t: any[]) => apiClient.updateEmployeeTools(employeeId, t),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employee", employeeId] }),
  });
  const toggle = (name: string) => {
    const set = new Set<string>(tools.map((t) => (typeof t === "string" ? t : t.name)));
    if (set.has(name)) {
      set.delete(name);
    } else {
      set.add(name);
    }
    const arr = Array.from(set);
    setTools(arr);
  };
  return (
    <div className="space-y-2 text-sm">
      {knownTools.map((t) => {
        const enabled = tools.some((x) => (typeof x === "string" ? x === t : x?.name === t));
        return (
          <label key={t} className="flex items-center gap-2">
            <input type="checkbox" checked={enabled} onChange={() => toggle(t)} />
            <span>{t}</span>
          </label>
        );
      })}
      <div>
        <button className="mt-2 px-3 py-1 border rounded" onClick={() => mu.mutate(tools)} disabled={mu.isPending}>Save</button>
      </div>
    </div>
  );
}


