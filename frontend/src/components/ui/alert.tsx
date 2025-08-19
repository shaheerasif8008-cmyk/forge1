import * as React from "react";

export function Alert({ children, variant = "default" }: { children: React.ReactNode; variant?: "default" | "destructive" }) {
  return (
    <div className={`w-full rounded-md border p-3 text-sm ${variant === "destructive" ? "border-destructive text-destructive" : "border-border"}`}>
      {children}
    </div>
  );
}


