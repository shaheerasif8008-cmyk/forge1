"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiClient, type User } from "./api";
import config from "./config";

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Token management functions
  const getToken = (): string | null => {
    if (config.useLocalStorageAuth) {
      try {
        return localStorage.getItem("forge1_token");
      } catch {
        return null;
      }
    }
    // For httpOnly cookies, token would be handled by the browser automatically
    return token;
  };

  const setToken = (newToken: string | null) => {
    setTokenState(newToken);
    if (config.useLocalStorageAuth) {
      try {
        if (newToken) {
          localStorage.setItem("forge1_token", newToken);
        } else {
          localStorage.removeItem("forge1_token");
        }
      } catch {
        // Handle localStorage errors gracefully
      }
    }
  };

  const onUnauthorized = () => {
    setToken(null);
    setUser(null);
  };

  // Initialize API client
  useEffect(() => {
    apiClient.init(getToken, setToken, onUnauthorized);
  }, []);

  // Load initial token and user info
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = getToken();
      if (storedToken) {
        setTokenState(storedToken);
        try {
          const userData = await apiClient.getMe();
          setUser(userData);
        } catch {
          // Token is invalid, clear it
          setToken(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await apiClient.login(email, password);
      setToken(response.access_token);
      
      // Fetch user info
      const userData = await apiClient.getMe();
      setUser(userData);
    } catch (error) {
      throw error;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    logout,
    isAuthenticated: !!token && !!user,
    loading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}