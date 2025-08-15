import axios from 'axios'

const baseURL: string = (import.meta as any).env?.VITE_TESTING_API_BASE_URL || 'http://localhost:8000'

export const testingApi = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

testingApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('testing_admin_jwt') || (import.meta as any).env?.VITE_TESTING_ADMIN_JWT
  if (token) {
    const headers: Record<string, string> = (config.headers as any) || {}
    if (!headers["Authorization"]) headers["Authorization"] = `Bearer ${token}`
    if (!headers["X-Testing-Service-Key"]) headers["X-Testing-Service-Key"] = String(token)
    config.headers = headers as any
  }
  return config
})


