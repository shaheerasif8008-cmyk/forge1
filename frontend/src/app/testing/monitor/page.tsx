"use client";

import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSSE } from "@/hooks/useSSE";
import config from "@/lib/config";

function buildEventsUrl(token?: string, type?: string) {
	const u = new URL(`${config.apiBaseUrl.replace(/\/$/, "")}/api/v1/ai-comms/events`);
	if (token) u.searchParams.set("token", token);
	if (type) u.searchParams.set("type", type);
	return u.toString();
}

export default function MonitorPage() {
	const [typeFilter, setTypeFilter] = useState<string>("");
	const [paused, setPaused] = useState(false);
	const token = config.eventsToken;
	const url = useMemo(() => buildEventsUrl(token, typeFilter || undefined), [typeFilter, token]);
	const { data, isConnected, error, reconnect } = useSSE({ url, enabled: !paused });

	// KPIs: last 100 messages
	const kpis = useMemo(() => {
		const last = data.slice(0, 100);
		const total = last.length;
		let errors = 0;
		for (const ev of last) {
			if (ev && typeof ev === "object") {
				const rec = ev as Record<string, unknown>;
				if (rec["level"] === "error") errors += 1;
			}
		}
		return { total, errors };
	}, [data]);

	useEffect(() => {
		if (error) {
			// noop here; surface visually
		}
	}, [error]);

	return (
		<div className="space-y-6">
			<div className="flex items-center justify-between">
				<h1 className="text-2xl font-semibold">Live Monitor</h1>
				<div className="flex items-center gap-2">
					<Input placeholder="Filter by type (e.g. testpack)" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-64" />
					<Button variant="outline" onClick={() => setPaused((p) => !p)}>{paused ? "Resume" : "Pause"}</Button>
					<Button variant="outline" onClick={reconnect}>Reconnect</Button>
				</div>
			</div>

			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				<Card className="shadow-card"><CardContent className="p-4"><div className="text-sm text-muted-foreground">Messages</div><div className="text-2xl font-semibold">{kpis.total}</div></CardContent></Card>
				<Card className="shadow-card"><CardContent className="p-4"><div className="text-sm text-muted-foreground">Errors</div><div className="text-2xl font-semibold">{kpis.errors}</div></CardContent></Card>
				<Card className="shadow-card"><CardContent className="p-4"><div className="text-sm text-muted-foreground">Status</div><div className="text-2xl font-semibold">{isConnected ? "Connected" : "Disconnected"}</div></CardContent></Card>
			</div>

			<Card className="shadow-card">
				<CardHeader>
					<CardTitle>Events</CardTitle>
					<CardDescription>Most recent first</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="max-h-[50vh] overflow-auto space-y-2">
						{data.map((ev, idx) => (
							<div key={idx} className="text-xs font-mono whitespace-pre-wrap border rounded p-2">
								{typeof ev === "string" ? ev : JSON.stringify(ev)}
							</div>
						))}
					</div>
					{error && <div className="text-danger text-sm mt-3">{error}</div>}
				</CardContent>
			</Card>
		</div>
	);
}