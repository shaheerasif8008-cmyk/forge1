"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiClient, type User } from "./api";
import config from "./config";

interface AuthContextType {
	user: User | null;
	token: string | null;
	refreshToken: string | null;
	login: (email: string, password: string) => Promise<void>;
	logout: () => Promise<void>;
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
	const [refreshToken, setRefreshTokenState] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);

	// Token management functions
	const getAccessToken = (): string | null => {
		if (config.useLocalStorageAuth) {
			try {
				return localStorage.getItem("forge1_token");
			} catch {
				return null;
			}
		}
		return token;
	};

	const getRefreshToken = (): string | null => {
		if (config.useLocalStorageAuth) {
			try {
				return localStorage.getItem("forge1_refresh_token");
			} catch {
				return null;
			}
		}
		return refreshToken;
	};

	const setTokens = (access: string | null, refresh?: string | null) => {
		setTokenState(access);
		if (typeof refresh !== "undefined") {
			setRefreshTokenState(refresh);
		}
		if (config.useLocalStorageAuth) {
			try {
				if (access) localStorage.setItem("forge1_token", access);
				else localStorage.removeItem("forge1_token");
				if (typeof refresh !== "undefined") {
					if (refresh) localStorage.setItem("forge1_refresh_token", refresh);
					else localStorage.removeItem("forge1_refresh_token");
				}
			} catch {
				// ignore
			}
		}
	};

	const onUnauthorized = () => {
		setTokens(null, "");
		setUser(null);
	};

	// Initialize API client
	useEffect(() => {
		apiClient.init(getAccessToken, setTokens, onUnauthorized, getRefreshToken);
	}, []);

	// Load initial token and user info
	useEffect(() => {
		const initAuth = async () => {
			const storedToken = getAccessToken();
			const storedRefresh = getRefreshToken();
			if (storedToken) {
				setTokenState(storedToken);
				if (storedRefresh) setRefreshTokenState(storedRefresh);
				try {
					const userData = await apiClient.getMe();
					setUser(userData);
				} catch {
					// try refresh if available
					if (storedRefresh) {
						try {
							const pair = await apiClient.refresh(storedRefresh);
							setTokens(pair.access_token, pair.refresh_token);
							const userData = await apiClient.getMe();
							setUser(userData);
						} catch {
							setTokens(null, "");
						}
					} else {
						setTokens(null, "");
					}
				}
			}
			setLoading(false);
		};

		initAuth();
	}, []);

	const login = async (email: string, password: string) => {
		// Prefer v2; fallback to v1 demo if 403/404
		try {
			const r = await apiClient.loginV2(email, password);
			setTokens(r.access_token, r.refresh_token);
		    } catch (e: unknown) {
      const code = (e as { response?: { status?: number } })?.response?.status;
      if (code === 403 || code === 404) {
        const r1 = await apiClient.loginV1(email, password);
        setTokens(r1.access_token);
      } else {
        throw e;
      }
    }
		// Fetch user info
		const userData = await apiClient.getMe();
		setUser(userData);
	};

	const logout = async () => {
		const rt = getRefreshToken();
		try {
			if (rt) await apiClient.logout(rt);
		} catch {
			// ignore
		}
		setTokens(null, "");
		setUser(null);
	};

	const value: AuthContextType = {
		user,
		token,
		refreshToken,
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