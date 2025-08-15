"use client";

import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

type Props = {
	children: React.ReactNode;
	attribute?: string | string[];
	defaultTheme?: string;
	enableSystem?: boolean;
	disableTransitionOnChange?: boolean;
};

export function ThemeProvider({ children, ...props }: Props) {
	const p: Record<string, unknown> = { ...props };
	return <NextThemesProvider {...p}>{children}</NextThemesProvider>;
}