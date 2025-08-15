import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string

export const api = axios.create({
	baseURL: API_BASE_URL,
	withCredentials: false,
})

api.interceptors.request.use((config) => {
	const token = useAuthStore.getState().token
	if (token) {
		config.headers = config.headers ?? {}
		config.headers.Authorization = `Bearer ${token}`
	}
	return config
})

api.interceptors.response.use(
	(response) => response,
	(error) => {
		return Promise.reject(error)
	},
)
