import config from "../config";

const base = (import.meta.env.VITE_TESTING_API_URL as string) || "http://localhost:8002";
const svcKey = (import.meta.env.VITE_TESTING_SERVICE_KEY as string) || "";

function headers(): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (svcKey) h["X-Testing-Service-Key"] = svcKey;
  return h;
}

export async function listSuites(): Promise<Array<{id:number;name:string;target_env:string}>> {
  const r = await fetch(`${base}/api/v1/suites`, { headers: headers() });
  if (!r.ok) throw new Error("suites_failed");
  return r.json();
}

export async function createSuite(payload: any): Promise<{id:number}> {
  const r = await fetch(`${base}/api/v1/suites`, { method: "POST", headers: headers(), body: JSON.stringify(payload) });
  if (!r.ok) throw new Error("create_suite_failed");
  return r.json();
}

export async function listRuns(): Promise<any[]> {
  const r = await fetch(`${base}/api/v1/runs`, { headers: headers() });
  if (!r.ok) throw new Error("runs_failed");
  return r.json();
}

export async function createRun(suite_id: number, target_api_url?: string): Promise<{run_id:number}> {
  const r = await fetch(`${base}/api/v1/runs`, { method: "POST", headers: headers(), body: JSON.stringify({ suite_id, target_api_url }) });
  if (!r.ok) throw new Error("create_run_failed");
  return r.json();
}

export async function getRun(id: number): Promise<any> {
  const r = await fetch(`${base}/api/v1/runs/${id}`, { headers: headers() });
  if (!r.ok) throw new Error("get_run_failed");
  return r.json();
}

export async function seedBaseline(): Promise<{suite_id:number}> {
  const r = await fetch(`${base}/api/v1/seed`, { method: "POST", headers: headers() });
  if (!r.ok) throw new Error("seed_failed");
  return r.json();
}


