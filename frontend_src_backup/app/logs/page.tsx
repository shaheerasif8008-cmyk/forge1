"use client";

import { useSSE } from "@/hooks/useSSE";

export default function LogsPage() {
  const { data } = useSSE<{ message: string; ts: string }>({ url: `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/logs` });
  return (
    <div className="space-y-2">
      {data.length ? (
        <ul className="space-y-1 text-xs">
          {data.map((l, i) => (
            <li key={i} className="font-mono">[{l.ts}] {l.message}</li>
          ))}
        </ul>
      ) : (
        <div className="text-sm text-muted-foreground">No logs yet — runs will appear here in real time.</div>
      )}
    </div>
  );
}


