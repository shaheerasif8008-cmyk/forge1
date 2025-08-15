"use client";

import { useEffect, useMemo, useState } from "react";
import { testingApi, type RunListItem, type RunDetail } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

export default function HistoryPage() {
	const [runs, setRuns] = useState<RunListItem[] | null>(null);
	const [selected, setSelected] = useState<number[]>([]);
	const [filter, setFilter] = useState("");
	const [details, setDetails] = useState<Record<number, RunDetail | undefined>>({});

	useEffect(() => {
		let mounted = true;
		testingApi.listRuns(50).then((r) => {
			if (!mounted) return;
			setRuns(r);
		});
		return () => {
			mounted = false;
		};
	}, []);

	const filtered = useMemo(() => {
		if (!runs) return null;
		const f = filter.trim().toLowerCase();
		if (!f) return runs;
		return runs.filter((r) => String(r.id).includes(f) || r.status.toLowerCase().includes(f));
	}, [runs, filter]);

	const toggleSelect = (id: number) => {
		setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : prev.length >= 2 ? [prev[1], id] : [...prev, id]));
	};

	const loadDetail = async (id: number) => {
		if (details[id]) return;
		const d = await testingApi.getRun(id);
		setDetails((prev) => ({ ...prev, [id]: d }));
	};

	return (
		<div className="space-y-6">
			<div className="flex items-center justify-between">
				<h1 className="text-2xl font-semibold">Run History</h1>
				<Input placeholder="Filter by id or status" className="w-64" value={filter} onChange={(e) => setFilter(e.target.value)} />
			</div>

			{!filtered ? (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					{Array.from({ length: 4 }).map((_, i) => (
						<Card key={i} className="shadow-card"><CardContent className="p-4"><Skeleton className="h-6 w-40" /><Skeleton className="h-4 w-24 mt-2" /></CardContent></Card>
					))}
				</div>
			) : (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					{filtered.map((r) => (
						<Card key={r.id} className="shadow-card">
							<CardHeader>
								<CardTitle>Run #{r.id}</CardTitle>
								<CardDescription>
									Status: <span className="font-mono text-xs px-1 py-0.5 bg-muted rounded">{r.status}</span>
								</CardDescription>
							</CardHeader>
							<CardContent>
								<div className="flex items-center gap-2">
									<Button variant={selected.includes(r.id) ? "secondary" : "outline"} onClick={() => toggleSelect(r.id)}>
										{selected.includes(r.id) ? "Selected" : "Select"}
									</Button>
									<Button variant="outline" onClick={() => loadDetail(r.id)}>Details</Button>
								</div>
								{details[r.id] && (
									<div className="mt-3 text-xs font-mono whitespace-pre-wrap border rounded p-2">
										{JSON.stringify(details[r.id]?.run?.stats || {}, null, 2)}
									</div>
								)}
							</CardContent>
						</Card>
					))}
				</div>
			)}

			{selected.length === 2 && (
				<Card className="shadow-card">
					<CardHeader>
						<CardTitle>Compare Runs</CardTitle>
						<CardDescription>#{selected[0]} vs #{selected[1]}</CardDescription>
					</CardHeader>
					<CardContent>
						<div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
							<div className="border rounded p-2">
								{details[selected[0]] ? JSON.stringify(details[selected[0]]?.run?.stats || {}, null, 2) : "Load details to compare"}
							</div>
							<div className="border rounded p-2">
								{details[selected[1]] ? JSON.stringify(details[selected[1]]?.run?.stats || {}, null, 2) : "Load details to compare"}
							</div>
						</div>
					</CardContent>
				</Card>
			)}
		</div>
	);
}