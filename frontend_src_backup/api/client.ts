import config from "../config";

type Tokens = { accessToken: string; refreshToken?: string | null };

let getTokens: () => Tokens = () => ({ accessToken: "", refreshToken: null });
let setTokens: (t: Tokens) => void = () => {};
let onLogout: () => void = () => {};

let refreshPromise: Promise<string> | null = null;

const cookieMode = (import.meta.env.VITE_AUTH_COOKIE_MODE || "false") === "true";

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;
  const { refreshToken } = getTokens();
  if (!refreshToken) {
    throw new Error("no_refresh_token");
  }
  refreshPromise = (async () => {
    const resp = await fetch(`${config.apiUrl}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      credentials: cookieMode ? "include" : "same-origin",
    });
    if (!resp.ok) throw new Error("refresh_failed");
    const data = (await resp.json()) as { access_token: string; refresh_token?: string };
    const next: Tokens = { accessToken: data.access_token, refreshToken: data.refresh_token ?? refreshToken };
    setTokens(next);
    return next.accessToken;
  })();
  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  if (!cookieMode) {
    const { accessToken } = getTokens();
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  }
  const resp = await fetch(input, { ...init, headers, credentials: cookieMode ? "include" : init.credentials });
  if (resp.status !== 401) return resp;
  // Attempt refresh and retry once
  try {
    const newAccess = await refreshAccessToken();
    const retryHeaders = new Headers(init.headers || {});
    if (!cookieMode) retryHeaders.set("Authorization", `Bearer ${newAccess}`);
    return await fetch(input, { ...init, headers: retryHeaders, credentials: cookieMode ? "include" : init.credentials });
  } catch {
    onLogout();
    return resp;
  }
}

export function initApiClient(opts: {
  getTokens: () => Tokens;
  setTokens: (t: Tokens) => void;
  onLogout: () => void;
}) {
  getTokens = opts.getTokens;
  setTokens = opts.setTokens;
  onLogout = opts.onLogout;
}


