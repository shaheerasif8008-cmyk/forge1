import axios from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach Authorization header from localStorage
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("forge1_token");
    if (token) {
      config.headers = config.headers ?? {};
      (config.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status ?? 0;
    const message = error?.response?.data?.message ?? error?.message ?? "Request failed";
    if (typeof window !== "undefined") {
      if (status === 401) {
        try { localStorage.removeItem("forge1_token"); } catch {}
        if (!window.location.pathname.startsWith("/login")) {
          window.location.href = "/login";
        }
      } else if (status === 403) {
        if (!window.location.pathname.startsWith("/forbidden")) {
          window.location.href = "/forbidden";
        }
      }
    }
    return Promise.reject({ status, message, original: error });
  }
);

export type ApiError = {
  status: number;
  message: string;
  original?: unknown;
};


