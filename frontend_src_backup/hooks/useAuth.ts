"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

type LoginResponse = { access_token: string; role?: string };

const TOKEN_KEY = "forge1_token";

export function useAuth() {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | undefined>(undefined);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem(TOKEN_KEY);
    if (stored) setToken(stored);
    setInitializing(false);
  }, []);

  const isAuthenticated = !!token;

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<LoginResponse>("/api/v1/auth/login", { email, password });
    const jwt = res.data.access_token;
    setToken(jwt);
    try { localStorage.setItem(TOKEN_KEY, jwt); } catch {}
    setRole(res.data.role);
    return res.data;
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    await api.post("/api/v1/auth/signup", { email, password });
  }, []);

  const forgot = useCallback(async (email: string) => {
    await api.post("/api/v1/auth/forgot", { email });
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setRole(undefined);
    try { localStorage.removeItem(TOKEN_KEY); } catch {}
    if (typeof window !== "undefined") window.location.href = "/login";
  }, []);

  const value = useMemo(
    () => ({ token, role, isAuthenticated, initializing, login, signup, forgot, logout }),
    [token, role, isAuthenticated, initializing, login, signup, forgot, logout]
  );

  return value;
}


