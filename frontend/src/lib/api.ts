import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios'
import Cookies from 'js-cookie'
import toast from 'react-hot-toast'
import { ApiResponse } from './types'

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = Cookies.get('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling and token refresh
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as any

    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = Cookies.get('refreshToken')
        if (refreshToken) {
          const response = await axios.post(
            `${process.env.NEXT_PUBLIC_API_BASE_URL}/auth/refresh`,
            { refreshToken }
          )
          
          const { token, refreshToken: newRefreshToken } = response.data
          
          // Update tokens
          Cookies.set('token', token, { expires: 7, secure: true, sameSite: 'strict' })
          Cookies.set('refreshToken', newRefreshToken, { expires: 30, secure: true, sameSite: 'strict' })
          
          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${token}`
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        Cookies.remove('token')
        Cookies.remove('refreshToken')
        
        // Only redirect if we're not already on the login page
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      }
    }

    // Handle other errors
    const errorMessage = (error.response?.data as any)?.message || error.message || 'An error occurred'
    
    // Don't show toasts for certain status codes or on auth endpoints
    const isAuthEndpoint = error.config?.url?.includes('/auth/')
    const shouldShowToast = !isAuthEndpoint && error.response?.status !== 401

    if (shouldShowToast) {
      toast.error(errorMessage)
    }

    return Promise.reject(error)
  }
)

// API helper functions
export class ApiService {
  // Authentication
  static async login(email: string, password: string) {
    const response = await apiClient.post('/auth/login', { email, password })
    return response.data
  }

  static async register(data: { email: string; password: string; firstName: string; lastName: string }) {
    const response = await apiClient.post('/auth/register', data)
    return response.data
  }

  static async logout() {
    const response = await apiClient.post('/auth/logout')
    return response.data
  }

  static async refreshToken(refreshToken: string) {
    const response = await apiClient.post('/auth/refresh', { refreshToken })
    return response.data
  }

  // User profile
  static async getProfile() {
    const response = await apiClient.get('/user/profile')
    return response.data
  }

  static async updateProfile(data: Partial<{ firstName: string; lastName: string; email: string }>) {
    const response = await apiClient.put('/user/profile', data)
    return response.data
  }

  // AI Employees
  static async getEmployees(page = 1, limit = 10) {
    const response = await apiClient.get(`/employees?page=${page}&limit=${limit}`)
    return response.data
  }

  static async getEmployee(id: string) {
    const response = await apiClient.get(`/employees/${id}`)
    return response.data
  }

  static async createEmployee(data: any) {
    const response = await apiClient.post('/employees', data)
    return response.data
  }

  static async updateEmployee(id: string, data: any) {
    const response = await apiClient.put(`/employees/${id}`, data)
    return response.data
  }

  static async deleteEmployee(id: string) {
    const response = await apiClient.delete(`/employees/${id}`)
    return response.data
  }

  static async startEmployee(id: string) {
    const response = await apiClient.post(`/employees/${id}/start`)
    return response.data
  }

  static async stopEmployee(id: string) {
    const response = await apiClient.post(`/employees/${id}/stop`)
    return response.data
  }

  static async getEmployeeLogs(id: string, page = 1, limit = 50) {
    const response = await apiClient.get(`/employees/${id}/logs?page=${page}&limit=${limit}`)
    return response.data
  }

  static async getEmployeePerformance(id: string, period = '7d') {
    const response = await apiClient.get(`/employees/${id}/performance?period=${period}`)
    return response.data
  }

  // Dashboard
  static async getDashboardStats() {
    const response = await apiClient.get('/dashboard/stats')
    return response.data
  }

  static async getRecentActivity(limit = 10) {
    const response = await apiClient.get(`/dashboard/activity?limit=${limit}`)
    return response.data
  }

  // Billing & Subscription
  static async getSubscription() {
    const response = await apiClient.get('/billing/subscription')
    return response.data
  }

  static async getUsage() {
    const response = await apiClient.get('/billing/usage')
    return response.data
  }

  static async getInvoices(page = 1, limit = 10) {
    const response = await apiClient.get(`/billing/invoices?page=${page}&limit=${limit}`)
    return response.data
  }

  static async createCheckoutSession(priceId: string) {
    const response = await apiClient.post('/billing/checkout', { priceId })
    return response.data
  }

  static async cancelSubscription() {
    const response = await apiClient.post('/billing/cancel')
    return response.data
  }

  // Testing
  static async getTestSuites() {
    const response = await apiClient.get('/testing/suites')
    return response.data
  }

  static async getTestSuite(id: string) {
    const response = await apiClient.get(`/testing/suites/${id}`)
    return response.data
  }

  static async runTestSuite(id: string, config?: any) {
    const response = await apiClient.post(`/testing/suites/${id}/run`, config)
    return response.data
  }

  static async getTestRuns(suiteId?: string, page = 1, limit = 10) {
    const params = new URLSearchParams({ page: page.toString(), limit: limit.toString() })
    if (suiteId) params.append('suiteId', suiteId)
    
    const response = await apiClient.get(`/testing/runs?${params}`)
    return response.data
  }

  static async getTestRun(id: string) {
    const response = await apiClient.get(`/testing/runs/${id}`)
    return response.data
  }

  static async cancelTestRun(id: string) {
    const response = await apiClient.post(`/testing/runs/${id}/cancel`)
    return response.data
  }

  static async getTestLogs(runId: string, page = 1, limit = 100) {
    const response = await apiClient.get(`/testing/runs/${runId}/logs?page=${page}&limit=${limit}`)
    return response.data
  }
}

export default ApiService