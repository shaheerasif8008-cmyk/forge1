import axios, { AxiosError, AxiosHeaders, AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import config from "../config";

// Auth types (v1 legacy + v2)
export interface LoginResponseV1 {
  access_token: string;
  token_type: string;
  role?: string;
}

export interface LoginResponseV2 {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  user_id: string;
  tenant_id: string;
  email?: string;
  username?: string;
  roles?: string[];
}

export interface ApiError {
  detail: string;
  status?: number;
}

// Employees
export interface EmployeeIn {
  name: string;
  role_name: string;
  description: string;
  tools: Array<string | Record<string, unknown>>;
}

export interface EmployeeOut {
  id: string;
  name: string;
  tenant_id: string;
  owner_user_id: number | null;
  config: Record<string, unknown>;
}

export interface ExecuteIn {
  task: string;
  iterations?: number | null;
  context?: Record<string, unknown> | null;
}

export interface ExecuteOutResult {
  output: string;
  success?: boolean;
  error?: string | null;
  model_used?: string | null;
  metadata?: Record<string, unknown>;
  execution_time?: number;
}

export interface ExecuteOut {
  results: Array<Record<string, unknown>>; // backend returns model_dump list; keep generic here
  trace_id?: string;
}

export interface EmployeeLogOut {
  id: number;
  task_type: string;
  model_used: string | null;
  success: boolean;
  execution_time: number | null;
  error_message: string | null;
  created_at: string | null;
}

export interface EmployeePerformanceOut {
  success_ratio: number | null;
  avg_duration_ms: number | null;
  tasks: number;
  errors: number;
  tool_calls: number;
}

export type MemorySearchResult = {
  events: Array<{ id: number; kind: string; content: string; metadata?: Record<string, unknown>; score: number }>;
  facts: Array<{ id: number; fact: string; metadata?: Record<string, unknown>; source_event_id?: number | null; score: number }>;
};

export type ToolCall = {
  name: string;
  duration_ms?: number | null;
  status?: string | null;
  input?: Record<string, unknown> | null;
  output?: Record<string, unknown> | null;
};

export type TaskTrace = {
  task_id: number;
  model_used?: string | null;
  success: boolean;
  execution_time?: number | null;
  tool_calls: ToolCall[];
};

// Metrics
export interface ClientMetricsSummary {
  tasks: number;
  avg_duration_ms: number;
  success_ratio: number;
  tokens: number;
  cost_cents: number;
  by_day: Array<{
    day: string;
    tasks: number;
    avg_duration_ms: number;
    success_ratio: number;
    tokens: number;
    errors: number;
  }>;
}

// Health
export interface HealthResponse {
  status: string;
  postgres?: boolean;
  redis?: boolean;
  trace_id?: string;
}

// Testing API types
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

class ApiClient {
  private axios: AxiosInstance;
  private getToken: () => string | null = () => null;
  private getRefreshToken: () => string | null = () => null;
  private setTokens: (access: string | null, refresh?: string | null) => void = () => {};
  private onUnauthorized: () => void = () => {};

  constructor() {
    const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim();
    const defaultBase = baseUrl || "/api/proxy";
    this.axios = axios.create({
      baseURL: defaultBase,
      headers: { "Content-Type": "application/json" },
      withCredentials: false,
      timeout: 15000,
    });

    // Attach Authorization header
    this.axios.interceptors.request.use((req) => {
      const token = this.getToken?.();
      if (token) {
        const headers = new AxiosHeaders(req.headers);
        headers.set("Authorization", `Bearer ${token}`);
        req.headers = headers;
      }
      return req;
    });

    // Refresh on 401 using v2 endpoint if refresh token available
    this.axios.interceptors.response.use(
      (res) => res,
      async (error: AxiosError) => {
        try {
          if (typeof window !== "undefined") {
            const detail = (error.response?.data as any)?.detail || error.message || `HTTP ${error.response?.status || ""}`;
            window.dispatchEvent(new CustomEvent("forge1:api_error", { detail: { message: String(detail) } }));
          }
        } catch {}
        const original = (error.config ?? {}) as InternalAxiosRequestConfig & { _retry?: boolean };
        if (error.response?.status === 401 && !original._retry) {
          const refresh = this.getRefreshToken?.();
          if (refresh) {
            original._retry = true;
            try {
              const r = await axios.post<LoginResponseV2>(`${defaultBase}/api/v1/auth/refresh`, {
                refresh_token: refresh,
              });
              this.setTokens(r.data.access_token, r.data.refresh_token);
              // retry original with new token
              const headers = new AxiosHeaders(original.headers);
              headers.set("Authorization", `Bearer ${r.data.access_token}`);
              original.headers = headers;
              return this.axios.request(original);
            } catch {
              this.onUnauthorized?.();
            }
          }
          this.onUnauthorized?.();
        }
        // Map errors to a normalized shape
        const mapped: ApiError = {
          detail: (error.response?.data as any)?.detail || error.message || "Request failed",
          status: error.response?.status,
        };
        return Promise.reject(mapped);
      }
    );
  }

  init(
    getAccessToken: () => string | null,
    setTokens: (access: string | null, refresh?: string | null) => void,
    onUnauthorized: () => void,
    getRefreshToken?: () => string | null,
  ) {
    this.getToken = getAccessToken;
    this.getRefreshToken = getRefreshToken || (() => null);
    this.setTokens = setTokens;
    this.onUnauthorized = onUnauthorized;
  }

  // Auth (legacy v1)
  async loginV1(email: string, password: string): Promise<LoginResponseV1> {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const { data } = await this.axios.post<LoginResponseV1>("/api/v1/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return data;
  }

  // Auth v2 (password login, refresh, logout)
  async loginV2(email: string, password: string): Promise<LoginResponseV2> {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const { data } = await this.axios.post<LoginResponseV2>("/api/v1/auth/login-password", form);
    return data;
  }

  async refresh(refreshToken: string): Promise<LoginResponseV2> {
    const { data } = await this.axios.post<LoginResponseV2>("/api/v1/auth/refresh", { refresh_token: refreshToken });
    return data;
  }

  async logout(refreshToken: string): Promise<{ status: string }> {
    const { data } = await this.axios.post<{ status: string }>("/api/v1/auth/logout", { refresh_token: refreshToken });
    return data;
  }

  async getMe(): Promise<User> {
    const { data } = await this.axios.get<User>("/api/v1/auth/me");
    return data;
  }

  // Health
  async getHealth(): Promise<HealthResponse> {
    const { data } = await this.axios.get<HealthResponse>("/api/v1/health");
    return data;
  }

  // Employees CRUD
  async listEmployees(): Promise<EmployeeOut[]> {
    const { data } = await this.axios.get<EmployeeOut[]>("/api/v1/employees/");
    return data;
  }

  async createEmployee(payload: EmployeeIn): Promise<EmployeeOut> {
    const { data } = await this.axios.post<EmployeeOut>("/api/v1/employees/", payload);
    return data;
  }

  async getEmployee(employeeId: string): Promise<EmployeeOut> {
    const { data } = await this.axios.get<EmployeeOut>(`/api/v1/employees/${employeeId}`);
    return data;
  }

  async deleteEmployee(employeeId: string): Promise<void> {
    await this.axios.delete(`/api/v1/employees/${employeeId}`);
  }

  async runEmployee(employeeId: string, payload: ExecuteIn): Promise<ExecuteOut> {
    const { data } = await this.axios.post<ExecuteOut>(`/api/v1/employees/${employeeId}/run`, payload);
    return data;
  }

  async getEmployeeLogs(employeeId: string, limit = 20, offset = 0): Promise<EmployeeLogOut[]> {
    const { data } = await this.axios.get<EmployeeLogOut[]>(`/api/v1/employees/${employeeId}/logs`, {
      params: { limit, offset },
    });
    return data;
  }

  async getEmployeePerformance(employeeId: string): Promise<EmployeePerformanceOut> {
    const { data } = await this.axios.get<EmployeePerformanceOut>(`/api/v1/employees/${employeeId}/performance`);
    return data;
  }

  // Memory APIs
  async addEmployeeMemory(employeeId: string, content: string, kind?: string, metadata?: Record<string, unknown>): Promise<{ status: string; event_id: number }> {
    const body: Record<string, unknown> = { content };
    if (kind) body.kind = kind;
    if (metadata) body.metadata = metadata;
    const { data } = await this.axios.post<{ status: string; event_id: number }>(`/api/v1/employees/${employeeId}/memory/add`, body);
    return data;
  }

  async searchEmployeeMemory(employeeId: string, q: string, top_k = 5): Promise<MemorySearchResult> {
    const { data } = await this.axios.get<MemorySearchResult>(`/api/v1/employees/${employeeId}/memory/search`, { params: { q, top_k } });
    return data;
  }

  async getTaskTrace(taskId: number): Promise<TaskTrace> {
    const { data } = await this.axios.get<TaskTrace>(`/api/v1/reviews/${taskId}`);
    return data;
  }

  async updateEmployeeTools(employeeId: string, tools: any[]): Promise<EmployeeOut> {
    const { data } = await this.axios.patch<EmployeeOut>(`/api/v1/employees/${employeeId}/tools`, { tools });
    return data;
  }

  // Metrics
  async getClientMetricsSummary(hours = 24): Promise<ClientMetricsSummary> {
    try {
      const { data } = await this.axios.get<ClientMetricsSummary>("/api/v1/client/metrics/summary", {
        params: { hours },
      });
      // If totally empty, fall back to dashboard summary endpoint
      if (!data || (typeof data.tasks === "number" && data.tasks === 0 && (!data.by_day || data.by_day.length === 0))) {
        const fb = await this.axios.get<ClientMetricsSummary>("/api/v1/metrics/summary", { params: { hours } });
        return fb.data;
      }
      return data;
    } catch (err) {
      // Fallback to dashboard summary endpoint if client metrics unavailable
      const fb = await this.axios.get<ClientMetricsSummary>("/api/v1/metrics/summary", { params: { hours } });
      return fb.data;
    }
  }

  async getActiveEmployees(minutes = 5): Promise<{ active_employees: number }> {
    const { data } = await this.axios.get<{ active_employees: number }>("/api/v1/metrics/active", {
      params: { minutes },
    });
    return data;
  }

  // SSE helper: build AI comms stream URL with token query param
  buildEventsUrl(filters?: { type?: string; employee_id?: string }, token?: string | null): string {
    const qp = new URLSearchParams();
    if (filters?.type) qp.set("type", filters.type);
    if (filters?.employee_id) qp.set("employee_id", filters.employee_id);
    if (token) qp.set("token", token);
    const qs = qp.toString();
    const base = (process.env.NEXT_PUBLIC_API_BASE_URL || "/api/proxy").replace(/\/$/, "");
    return `${base}/api/v1/events${qs ? `?${qs}` : ""}`;
  }
}

// Testing API Client
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

export const apiClient = new ApiClient();
export const testingApi = new TestingApiClient();