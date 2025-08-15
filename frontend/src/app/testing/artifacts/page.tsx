"use client";

import { useEffect, useState } from "react";
import { testingApi, type RunDetail } from "@/lib/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import config from "@/lib/config";

function toAbsolute(url: string | null): string | null {
	if (!url) return null;
	if (url.startsWith("http://") || url.startsWith("https://")) return url;
	return `${config.testingApiBaseUrl.replace(/\/$/, "")}${url}`;
}

export default function ArtifactsPage() {
	const [runId, setRunId] = useState<string>("");
	const [detail, setDetail] = useState<RunDetail | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const load = async () => {
		if (!runId) return;
		setLoading(true);
		setError(null);
		try {
			const d = await testingApi.getRun(Number(runId));
			setDetail(d);
		} catch (e: unknown) {
			const msg = typeof e === "object" && e !== null && "message" in e ? String((e as { message?: unknown }).message || "") : "Failed to fetch run";
			setError(msg || "Failed to fetch run");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		// no-op
	}, []);

	return (
		<div className="space-y-6">
			<Card className="shadow-card">
				<CardHeader>
					<CardTitle>Artifacts</CardTitle>
					<CardDescription>Enter a run id to view its report and artifacts.</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="flex items-center gap-2">
						<Input placeholder="Run ID" value={runId} onChange={(e) => setRunId(e.target.value)} className="w-40" />
						<Button onClick={load} disabled={loading || !runId}>{loading ? "Loading..." : "Load"}</Button>
					</div>
					{error && <div className="text-danger text-sm mt-3">{error}</div>}
				</CardContent>
			</Card>

			{detail && (
				<Card className="shadow-card">
					<CardHeader>
						<CardTitle>Run #{detail.run.id} Report</CardTitle>
						<CardDescription>Status: {detail.run.status}</CardDescription>
					</CardHeader>
					<CardContent>
						{toAbsolute(detail.signed_report_url) ? (
							<iframe src={toAbsolute(detail.signed_report_url) as string} className="w-full h-[70vh] border rounded" />
						) : (
							<div className="text-sm text-muted-foreground">No report available. {toAbsolute(detail.report_html) && (<a href={toAbsolute(detail.report_html) as string} className="text-primary underline">Download HTML</a>)} {toAbsolute(detail.report_pdf) && (<a href={toAbsolute(detail.report_pdf) as string} className="text-primary underline ml-2">Download PDF</a>)}
							</div>
						)}
						{detail.artifacts?.length ? (
							<div className="mt-4">
								<h3 className="font-semibold mb-2">Artifacts</h3>
								<ul className="list-disc pl-5 text-sm">
									{detail.artifacts.map((a, i) => (
										<li key={i}><a href={toAbsolute(a) || "#"} target="_blank" className="text-primary underline">{toAbsolute(a)}</a></li>
									))}
								</ul>
							</div>
						) : null}
					</CardContent>
				</Card>
			)}
		</div>
	);
}