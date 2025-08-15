import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import config from "../config";
import { initApiClient } from "../api/client";

interface User {
  id: string;
  email?: string;
  username?: string;
  tenant_id: string;
  role?: string;
}

interface SessionContextType {
  user: User | null;
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
  loading: boolean;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function useSession() {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
}

interface SessionProviderProps {
  children: ReactNode;
}

export function SessionProvider({ children }: SessionProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // React to token changes: fetch user info when token is set; clear when removed
  useEffect(() => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    void fetchUserInfo(token);
  }, [token]);

  const fetchUserInfo = async (authToken: string) => {
    try {
      const response = await fetch(`${config.apiUrl}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      if (response.ok) {
        const userData = (await response.json()) as {
          user_id: string;
          tenant_id: string;
          email?: string;
          username?: string;
          roles?: string[];
        };
        setUser({
          id: userData.user_id,
          email: userData.email,
          username: userData.username,
          tenant_id: userData.tenant_id,
          role: Array.isArray(userData.roles) && userData.roles.length > 0 ? userData.roles[0] : undefined,
        });
      } else {
        // Token is invalid, clear user
        setUser(null);
      }
    } catch (error) {
      console.error("Failed to fetch user info:", error);
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = (authToken: string) => {
    setToken(authToken);
    // Optional persistence for demo UX
    if (import.meta.env.VITE_FEATURE_SESSION_MANAGEMENT === 'true') {
      try { sessionStorage.setItem('forge_token', authToken); } catch {}
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    try { sessionStorage.removeItem('forge_token'); } catch {}
  };

  // Initialize API client hooks
  useEffect(() => {
    initApiClient({
      getTokens: () => ({ accessToken: token || "", refreshToken: null }),
      setTokens: (t) => {
        if (t.accessToken) {
          setToken(t.accessToken);
        }
      },
      onLogout: () => logout(),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const value: SessionContextType = {
    user,
    token,
    login,
    logout,
    isAuthenticated: !!token && !!user,
    loading,
  };

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}
