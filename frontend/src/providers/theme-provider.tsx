"use client";

import * as React from "react";

export type ThemeProviderProps = {
  children: React.ReactNode;
  attribute?: string;
  defaultTheme?: string;
  enableSystem?: boolean;
  disableTransitionOnChange?: boolean;
};

export function ThemeProvider({ children }: ThemeProviderProps) {
  return <>{children}</>;
}