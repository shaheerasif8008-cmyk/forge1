import axios from 'axios'
import { authStore } from '../stores/auth'

const baseURL = import.meta.env.VITE_API_BASE_URL as string

export const api = axios.create({
	baseURL,
	headers: {
		'Content-Type': 'application/json',
	},
})

api.interceptors.request.use((config) => {
	const token = authStore.getState().token
	if (token) {
		config.headers = config.headers ?? {}
		config.headers.Authorization = `Bearer ${token}`
	}
	return config
})

api.interceptors.response.use(
	(response) => response,
	(error) => {
		if (error?.response?.status === 401) {
			authStore.getState().logout()
		}
		return Promise.reject(error)
	}
)