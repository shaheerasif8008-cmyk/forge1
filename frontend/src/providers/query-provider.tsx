"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";

interface QueryProviderProps {
	children: React.ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
	const [queryClient] = useState(
		() =>
			new QueryClient({
				defaultOptions: {
					queries: {
						staleTime: 60 * 1000,
						retry: (failureCount: number, error: { status?: number } | unknown) => {
							const status = typeof error === "object" && error && "status" in error ? (error as { status?: number }).status : undefined;
							if (status && status >= 400 && status < 500) return false;
							return failureCount < 3;
						},
					},
				},
			})
	);

	return (
		<QueryClientProvider client={queryClient}>
			<ApiErrorBanner />
			{children}
			{process.env.NODE_ENV === "development" && <ReactQueryDevtools />}
		</QueryClientProvider>
	);
}