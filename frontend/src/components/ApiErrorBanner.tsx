"use client";

import { useEffect, useState } from "react";

// Simple global fetch error banner. Shows when last API call failed.
export function ApiErrorBanner() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handler = (evt: Event) => {
      const e = evt as unknown as CustomEvent<{ message: string }>;
      setError(e.detail?.message || "API request failed");
      const t = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(t);
    };
    window.addEventListener("forge1:api_error", handler);
    return () => window.removeEventListener("forge1:api_error", handler);
  }, []);

  if (!error) return null;
  return (
    <div className="w-full bg-destructive text-destructive-foreground text-sm text-center py-2">
      {error}
    </div>
  );
}


