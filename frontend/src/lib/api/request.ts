export type RequestOptions = {
  signal?: AbortSignal;
  headers?: HeadersInit;
  timeoutMs?: number;
  retries?: number;
};

export async function request<T>(path: string, init?: RequestInit, opts?: RequestOptions): Promise<T> {
  const base = (process.env.NEXT_PUBLIC_API_BASE_URL || "/api/proxy").replace(/\/$/, "");
  const url = `${base}${path}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), opts?.timeoutMs ?? 10000);
  const retries = opts?.retries ?? 2;
  let lastErr: any;
  try {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(url, { ...init, signal: controller.signal });
        if (res.ok) {
          clearTimeout(timeout);
          return (await res.json()) as T;
        }
        // Retry on 429/503
        if (res.status === 429 || res.status === 503) {
          await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
          continue;
        }
        const detail = await safeDetail(res);
        throw new Error(`HTTP ${res.status}: ${detail}`);
      } catch (e: any) {
        lastErr = e;
        if (e?.name === "AbortError") break;
        if (attempt === retries) break;
        await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
      }
    }
    throw lastErr || new Error("request failed");
  } finally {
    clearTimeout(timeout);
  }
}

async function safeDetail(res: Response): Promise<string> {
  try {
    const j = (await res.json()) as any;
    return j?.detail || j?.error || res.statusText;
  } catch {
    return res.statusText;
  }
}


