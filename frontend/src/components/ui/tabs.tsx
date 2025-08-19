"use client";

import { createContext, useContext, useMemo, useState } from "react";

type TabsCtx = {
  value: string;
  setValue: (v: string) => void;
};

const Ctx = createContext<TabsCtx | null>(null);

export function Tabs({ defaultValue, className, children }: { defaultValue: string; className?: string; children: React.ReactNode }) {
  const [value, setValue] = useState(defaultValue);
  const ctx = useMemo(() => ({ value, setValue }), [value]);
  return (
    <Ctx.Provider value={ctx}>
      <div className={className}>{children}</div>
    </Ctx.Provider>
  );
}

export function TabsList({ children }: { children: React.ReactNode }) {
  return <div className="flex gap-2 mb-4">{children}</div>;
}

export function TabsTrigger({ value, children }: { value: string; children: React.ReactNode }) {
  const ctx = useContext(Ctx);
  if (!ctx) return null;
  const active = ctx.value === value;
  return (
    <button
      type="button"
      onClick={() => ctx.setValue(value)}
      className={`px-3 py-1 rounded border ${active ? "bg-primary text-primary-foreground" : "bg-card text-foreground"}`}
    >
      {children}
    </button>
  );
}

export function TabsContent({ value, children }: { value: string; children: React.ReactNode }) {
  const ctx = useContext(Ctx);
  if (!ctx) return null;
  if (ctx.value !== value) return null;
  return <div>{children}</div>;
}


