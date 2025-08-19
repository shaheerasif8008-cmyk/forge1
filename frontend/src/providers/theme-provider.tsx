"use client";

import * as React from "react";
import { useEffect, useState } from "react";

export type ThemeProviderProps = {
  children: React.ReactNode;
  attribute?: string;
  defaultTheme?: string;
  enableSystem?: boolean;
  disableTransitionOnChange?: boolean;
};

const STORAGE_KEY = "forge1:theme";

export function ThemeProvider({ children }: ThemeProviderProps) {
  const [mounted, setMounted] = useState(false);
  const [theme, setTheme] = useState<string>("light");

  useEffect(() => {
    // Hydrate from storage or prefers-color-scheme
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      const initial = saved || (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      setTheme(initial);
      const root = document.documentElement;
      if (initial === "dark") root.classList.add("dark");
      else root.classList.remove("dark");
    } catch {}
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
      const root = document.documentElement;
      if (theme === "dark") root.classList.add("dark");
      else root.classList.remove("dark");
    } catch {}
  }, [mounted, theme]);

  return <>{children}</>;
}

export function useThemeToggle(): { theme: "light" | "dark"; toggle: () => void } {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY) as "light" | "dark" | null;
      setTheme(saved === "dark" ? "dark" : "light");
    } catch {}
  }, []);
  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
      const root = document.documentElement;
      if (theme === "dark") root.classList.add("dark");
      else root.classList.remove("dark");
    } catch {}
  }, [theme]);
  return { theme, toggle: () => setTheme((t) => (t === "dark" ? "light" : "dark")) };
}