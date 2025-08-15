"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { useSSE } from "@/hooks/useSSE";

export default function EmployeeClient({ id }: { id: string }) {
	const employee = useQuery({
		queryKey: ["employee", id],
		queryFn: async () => (await api.get(`/api/v1/employees/${id}`)).data,
	});

	const { data: logs } = useSSE<{ message: string; ts: string }>({
		url: `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/logs?employee_id=${id}`,
	});

	return (
		<div className="space-y-3">
			<div className="text-xl font-semibold">{employee.data?.name ?? "Employee"}</div>
			<Tabs defaultValue="overview">
				<TabsList>
					<TabsTrigger value="overview">Overview</TabsTrigger>
					<TabsTrigger value="activity">Activity</TabsTrigger>
					<TabsTrigger value="metrics">Metrics</TabsTrigger>
					<TabsTrigger value="config">Config</TabsTrigger>
					<TabsTrigger value="logs">Logs</TabsTrigger>
				</TabsList>
				<TabsContent value="overview">
					<Card><CardContent className="p-4 text-sm text-muted-foreground">Overview content</CardContent></Card>
				</TabsContent>
				<TabsContent value="activity">
					<Card><CardContent className="p-4 text-sm text-muted-foreground">Recent activity</CardContent></Card>
				</TabsContent>
				<TabsContent value="metrics">
					<Card><CardContent className="p-4 text-sm text-muted-foreground">Metrics coming soon</CardContent></Card>
				</TabsContent>
				<TabsContent value="config">
					<Card><CardContent className="p-4 text-sm text-muted-foreground">Config editor</CardContent></Card>
				</TabsContent>
				<TabsContent value="logs">
					<Card>
						<CardContent className="p-4">
							{logs?.length ? (
								<ul className="space-y-1 text-xs">
									{logs.map((l, i) => (
										<li key={i} className="font-mono">[{l.ts}] {l.message}</li>
									))}
								</ul>
							) : (
								<div className="text-sm text-muted-foreground">No logs yet — runs will appear here in real time.</div>
							)}
						</CardContent>
					</Card>
				</TabsContent>
			</Tabs>
		</div>
	);
}
