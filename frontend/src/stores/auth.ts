import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import Cookies from 'js-cookie'
import { User, AuthResponse, LoginRequest, RegisterRequest } from '@/lib/types'
import { apiClient } from '@/lib/api'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
  clearError: () => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    (set, get) => ({
      // State
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: async (credentials: LoginRequest) => {
        try {
          set({ isLoading: true, error: null })
          
          const response = await apiClient.post<AuthResponse>('/auth/login', credentials)
          const { user, token, refreshToken } = response.data

          // Store tokens
          Cookies.set('token', token, { expires: 7, secure: true, sameSite: 'strict' })
          Cookies.set('refreshToken', refreshToken, { expires: 30, secure: true, sameSite: 'strict' })
          
          set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
            error: null
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.message || 'Login failed'
          })
          throw error
        }
      },

      register: async (data: RegisterRequest) => {
        try {
          set({ isLoading: true, error: null })
          
          const response = await apiClient.post<AuthResponse>('/auth/register', data)
          const { user, token, refreshToken } = response.data

          // Store tokens
          Cookies.set('token', token, { expires: 7, secure: true, sameSite: 'strict' })
          Cookies.set('refreshToken', refreshToken, { expires: 30, secure: true, sameSite: 'strict' })
          
          set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
            error: null
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.message || 'Registration failed'
          })
          throw error
        }
      },

      logout: () => {
        // Clear tokens
        Cookies.remove('token')
        Cookies.remove('refreshToken')
        
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null
        })
      },

      refreshToken: async () => {
        try {
          const refreshToken = Cookies.get('refreshToken')
          if (!refreshToken) {
            throw new Error('No refresh token available')
          }

          const response = await apiClient.post<AuthResponse>('/auth/refresh', {
            refreshToken
          })
          
          const { user, token, refreshToken: newRefreshToken } = response.data

          // Update tokens
          Cookies.set('token', token, { expires: 7, secure: true, sameSite: 'strict' })
          Cookies.set('refreshToken', newRefreshToken, { expires: 30, secure: true, sameSite: 'strict' })
          
          set({
            user,
            token,
            isAuthenticated: true,
            error: null
          })
        } catch (error) {
          // If refresh fails, logout user
          get().logout()
          throw error
        }
      },

      clearError: () => {
        set({ error: null })
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
)

// Initialize auth state from cookies on app start
export const initializeAuth = () => {
  const token = Cookies.get('token')
  const { user, isAuthenticated } = useAuthStore.getState()
  
  if (token && !isAuthenticated) {
    // Try to refresh token to validate it
    useAuthStore.getState().refreshToken().catch(() => {
      // If refresh fails, ensure user is logged out
      useAuthStore.getState().logout()
    })
  } else if (!token && isAuthenticated) {
    // Clear state if no token but user appears authenticated
    useAuthStore.getState().logout()
  }
}