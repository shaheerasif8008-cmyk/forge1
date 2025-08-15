"use client";

import { useEffect, useState } from "react";
import { testingApi, type SuiteSummary } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import toast from "react-hot-toast";

export default function SuitesPage() {
	const [suites, setSuites] = useState<SuiteSummary[] | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [runSuiteId, setRunSuiteId] = useState<number | null>(null);
	const [targetApiUrl, setTargetApiUrl] = useState<string>("");
	const [isSubmitting, setIsSubmitting] = useState(false);

	useEffect(() => {
		let mounted = true;
		testingApi
			.listSuites()
			.then((data) => {
				if (!mounted) return;
				setSuites(data);
			})
			.catch((e) => setError(e instanceof Error ? e.message : String(e)));
		return () => {
			mounted = false;
		};
	}, []);

	const triggerRun = async () => {
		if (!runSuiteId) return;
		setIsSubmitting(true);
		try {
			const res = await testingApi.createRun(runSuiteId, targetApiUrl || undefined);
			toast.success(`Run #${res.run_id} started`);
			setRunSuiteId(null);
			setTargetApiUrl("");
		} catch (e: unknown) {
			const msg = typeof e === "object" && e !== null && "message" in e ? String((e as { message?: unknown }).message || "") : "Failed to start run";
			toast.error(msg || "Failed to start run");
		} finally {
			setIsSubmitting(false);
		}
	};

	if (error) {
		return (
			<div className="space-y-4">
				<Card className="shadow-card">
					<CardHeader>
						<CardTitle>Suites</CardTitle>
						<CardDescription>Available test suites in staging.</CardDescription>
					</CardHeader>
					<CardContent>
						<div className="text-danger text-sm">{error}</div>
					</CardContent>
				</Card>
			</div>
		);
	}

	if (!suites) {
		return (
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{Array.from({ length: 6 }).map((_, i) => (
					<Card key={i} className="shadow-card">
						<CardHeader>
							<Skeleton className="h-5 w-32" />
							<Skeleton className="h-4 w-48" />
						</CardHeader>
						<CardContent>
							<Skeleton className="h-10 w-full" />
						</CardContent>
					</Card>
				))}
			</div>
		);
	}

	return (
		<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{suites.map((s) => (
				<Card key={s.id} className="shadow-card">
					<CardHeader>
						<CardTitle>{s.name}</CardTitle>
						<CardDescription>
							Target: <span className="font-mono text-xs px-1 py-0.5 bg-muted rounded">{s.target_env}</span>
						</CardDescription>
					</CardHeader>
					<CardContent>
						<div className="flex items-center gap-2">
							<Button onClick={() => setRunSuiteId(s.id)}>Run</Button>
							{s.has_load && <span className="text-xs text-muted-foreground">Load</span>}
							{s.has_chaos && <span className="text-xs text-muted-foreground">Chaos</span>}
							{s.has_security && <span className="text-xs text-muted-foreground">Security</span>}
						</div>
					</CardContent>
				</Card>
			))}

			{runSuiteId !== null && (
				<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
					<div className="bg-card text-card-foreground w-full max-w-md rounded-lg border shadow-card p-6">
						<h3 className="text-lg font-semibold mb-2">Run Suite</h3>
						<p className="text-sm text-muted-foreground mb-4">Optionally override target API URL for this run.</p>
						<Input placeholder="https://backend.example.com" value={targetApiUrl} onChange={(e) => setTargetApiUrl(e.target.value)} />
						<div className="mt-4 flex justify-end gap-2">
							<Button variant="ghost" onClick={() => setRunSuiteId(null)} disabled={isSubmitting}>Cancel</Button>
							<Button onClick={triggerRun} disabled={isSubmitting}>{isSubmitting ? "Starting..." : "Start Run"}</Button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}