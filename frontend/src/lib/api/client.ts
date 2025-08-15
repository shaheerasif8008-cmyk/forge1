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

export interface ExecuteOut {
  results: Array<Record<string, unknown>>;
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

class ApiClient {
  private axios: AxiosInstance;
  private getToken: () => string | null = () => null;
  private getRefreshToken: () => string | null = () => null;
  private setTokens: (access: string | null, refresh?: string | null) => void = () => {};
  private onUnauthorized: () => void = () => {};

  constructor() {
    this.axios = axios.create({
      baseURL: config.apiBaseUrl,
      headers: { "Content-Type": "application/json" },
      withCredentials: false,
    });

    this.axios.interceptors.request.use((req) => {
      const token = this.getToken?.();
      if (token) {
        const headers = new AxiosHeaders(req.headers);
        headers.set("Authorization", `Bearer ${token}`);
        req.headers = headers;
      }
      return req;
    });

    this.axios.interceptors.response.use(
      (res) => res,
      async (error: AxiosError) => {
        const original = (error.config ?? {}) as InternalAxiosRequestConfig & { _retry?: boolean };
        if (error.response?.status === 401 && !original._retry) {
          const refresh = this.getRefreshToken?.();
          if (refresh) {
            original._retry = true;
            try {
              const r = await axios.post<import("./client").LoginResponseV2>(`${config.apiBaseUrl}/api/v1/auth/refresh`, {
                refresh_token: refresh,
              });
              this.setTokens(r.data.access_token, r.data.refresh_token);
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
        return Promise.reject(error);
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

  // Metrics
  async getClientMetricsSummary(hours = 24): Promise<ClientMetricsSummary> {
    const { data } = await this.axios.get<ClientMetricsSummary>("/api/v1/client/metrics/summary", {
      params: { hours },
    });
    return data;
  }

  async getActiveEmployees(minutes = 5): Promise<{ active_employees: number }> {
    const { data } = await this.axios.get<{ active_employees: number }>("/api/v1/client/metrics/active", {
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
    return `${config.apiBaseUrl}/api/v1/ai-comms/events${qs ? `?${qs}` : ""}`;
  }
}

export const apiClient = new ApiClient();