import config from "../config";

export type SuiteSummary = {
	id: number;
	name: string;
	target_env: "staging" | "prod" | string;
	has_load: boolean;
	has_chaos: boolean;
	has_security: boolean;
};

export type RunListItem = {
	id: number;
	suite_id: number;
	status: "running" | "pass" | "fail" | "aborted" | string;
	started_at: string | null;
	finished_at: string | null;
};

export type Finding = {
	id: number;
	severity: "critical" | "high" | "medium" | "low" | string;
	area: string;
	message: string;
};

export type RunDetail = {
	run: {
		id: number;
		suite_id: number;
		started_at: string | null;
		finished_at: string | null;
		status: RunListItem["status"];
		stats: Record<string, unknown>;
		artifacts: string[];
		target_api_url: string;
		findings: Omit<Finding, "id">[];
	};
	report_html: string | null;
	report_pdf: string | null;
	signed_report_url: string | null;
	artifacts: string[];
};

export class TestingApiClient {
	private baseUrl: string;
	private serviceKey?: string;

	constructor(baseUrl?: string, serviceKey?: string) {
		this.baseUrl = (baseUrl || config.testingApiBaseUrl).replace(/\/$/, "");
		this.serviceKey = serviceKey || config.testingServiceKey || process.env.NEXT_PUBLIC_TESTING_SERVICE_KEY;
	}

	private headers(json = true): HeadersInit {
		const h: Record<string, string> = {};
		if (json) h["Content-Type"] = "application/json";
		if (this.serviceKey) h["x-testing-service-key"] = String(this.serviceKey);
		return h;
	}

	private async _req<T>(path: string, init?: RequestInit): Promise<T> {
		const url = `${this.baseUrl}${path}`;
		const headers: HeadersInit = { ...(init?.headers || {}), ...this.headers(!(init && "headers" in init)) };
		const res = await fetch(url, {
			...init,
			headers,
			cache: "no-store",
		});
		if (!res.ok) {
			let detail = `${res.status}`;
			try {
				const j = (await res.json()) as unknown as { detail?: string; error?: string };
				detail = (j && (j.detail || j.error || JSON.stringify(j))) || detail;
			} catch {}
			throw new Error(`HTTP ${res.status}: ${detail}`);
		}
		return (await res.json()) as T;
	}

	listSuites(): Promise<SuiteSummary[]> {
		return this._req(`/api/v1/suites`);
	}

	createRun(suiteId: number, targetApiUrl?: string): Promise<{ run_id: number }> {
		const body: Record<string, unknown> = { suite_id: suiteId };
		if (targetApiUrl) body["target_api_url"] = targetApiUrl;
		return this._req(`/api/v1/runs`, { method: "POST", body: JSON.stringify(body) });
	}

	listRuns(limit = 50): Promise<RunListItem[]> {
		const q = new URLSearchParams({ limit: String(limit) }).toString();
		return this._req(`/api/v1/runs?${q}`);
	}

	getRun(runId: number): Promise<RunDetail> {
		return this._req(`/api/v1/runs/${runId}`);
	}
}

export const testingApi = new TestingApiClient();