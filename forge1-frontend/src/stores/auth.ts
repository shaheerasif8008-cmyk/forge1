import { create } from 'zustand'

export type AuthUser = {
	id: string
	email: string
	name?: string
	role?: 'client' | 'admin'
}

type AuthState = {
	token: string | null
	user: AuthUser | null
	isLoading: boolean
	login: (email: string, password: string) => Promise<void>
	register: (email: string, password: string, name?: string) => Promise<void>
	fetchMe: () => Promise<void>
	logout: () => void
}

const TOKEN_KEY = 'forge1_token'

export const authStore = create<AuthState>((set, get) => ({
	token: localStorage.getItem(TOKEN_KEY),
	user: null,
	isLoading: false,
	login: async (email: string, password: string) => {
		set({ isLoading: true })
		try {
			const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/auth/login`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, password }),
			})
			if (!res.ok) throw new Error('Login failed')
			const data = await res.json()
			const token = data?.access_token || data?.token || data?.jwt
			if (!token) throw new Error('Token missing')
			localStorage.setItem(TOKEN_KEY, token)
			set({ token })
			await get().fetchMe()
		} finally {
			set({ isLoading: false })
		}
	},
	register: async (email: string, password: string, name?: string) => {
		set({ isLoading: true })
		try {
			const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/auth/register`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, password, name }),
			})
			if (!res.ok) throw new Error('Register failed')
			await get().login(email, password)
		} finally {
			set({ isLoading: false })
		}
	},
	fetchMe: async () => {
		const token = get().token
		if (!token) return
		const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/users/me`, {
			headers: { Authorization: `Bearer ${token}` },
		})
		if (res.ok) {
			const user = await res.json()
			set({ user })
		}
	},
	logout: () => {
		localStorage.removeItem(TOKEN_KEY)
		set({ token: null, user: null })
	},
}))