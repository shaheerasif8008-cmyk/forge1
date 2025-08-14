import config from "./config";

// Types for API responses
export interface LoginResponse {
  access_token: string;
  token_type: string;
  role?: string;
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

class ApiClient {
  private baseUrl: string;
  private getToken: () => string | null;
  private setToken: (token: string | null) => void;
  private onUnauthorized: () => void;

  constructor() {
    this.baseUrl = config.apiBaseUrl;
    this.getToken = () => null;
    this.setToken = () => {};
    this.onUnauthorized = () => {};
  }

  // Initialize with token management functions
  init(
    getToken: () => string | null,
    setToken: (token: string | null) => void,
    onUnauthorized: () => void
  ) {
    this.getToken = getToken;
    this.setToken = setToken;
    this.onUnauthorized = onUnauthorized;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getToken();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string> | undefined),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (response.status === 401) {
        this.onUnauthorized();
        throw new Error("Unauthorized");
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error((errorData as ApiError).detail || `HTTP ${response.status}`);
      }

      return (await response.json()) as T;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error("Network error");
    }
  }

  // Auth endpoints
  async login(email: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    return this.request<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData.toString(),
    });
  }

  async getMe(): Promise<User> {
    return this.request<User>("/api/v1/auth/me");
  }

  async signup(email: string, password: string, tenantName?: string): Promise<void> {
    return this.request<void>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        tenant_name: tenantName || null,
      }),
    });
  }

  async forgotPassword(email: string): Promise<void> {
    return this.request<void>("/api/v1/auth/request-password-reset", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  }

  // Health check
  async getHealth(): Promise<{ status: string; postgres?: boolean; redis?: boolean }> {
    return this.request<{ status: string; postgres?: boolean; redis?: boolean }>("/api/v1/health");
  }
}

export const apiClient = new ApiClient();