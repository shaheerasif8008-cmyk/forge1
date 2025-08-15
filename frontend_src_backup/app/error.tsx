"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html>
      <body>
        <div className="mx-auto mt-24 max-w-md rounded-xl border bg-card p-6 text-center shadow-card">
          <div className="text-lg font-semibold">Something went wrong</div>
          <p className="mt-1 text-sm text-muted-foreground">An unexpected error occurred. Please try again.</p>
          <div className="mt-4">
            <Button onClick={() => reset()}>Retry</Button>
          </div>
        </div>
      </body>
    </html>
  );
}


