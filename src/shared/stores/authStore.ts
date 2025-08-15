import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
	token: string | null
	userEmail: string | null
	isAuthenticated: boolean
	login: (token: string, email?: string | null) => void
	logout: () => void
}

export const useAuthStore = create<AuthState>()(
	persist(
		(set) => ({
			token: null,
			userEmail: null,
			isAuthenticated: false,
			login: (token, email) => set({ token, userEmail: email ?? null, isAuthenticated: true }),
			logout: () => set({ token: null, userEmail: null, isAuthenticated: false }),
		}),
		{ name: 'forge1-auth' },
	),
)
