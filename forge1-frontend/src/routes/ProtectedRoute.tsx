import type { ReactNode } from 'react'
import { useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { authStore } from '../stores/auth'

export function ProtectedRoute({ children }: { children: ReactNode }) {
	const { token, user, fetchMe } = authStore()
	const location = useLocation()

	useEffect(() => {
		if (token && !user) {
			fetchMe().catch(() => {})
		}
	}, [token, user, fetchMe])

	if (!token) {
		return <Navigate to="/login" replace state={{ from: location }} />
	}
	return <>{children}</>
}