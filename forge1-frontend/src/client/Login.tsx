import type { FormEvent } from 'react'
import { useState } from 'react'
import { authStore } from '../stores/auth'
import { useNavigate, useLocation, Link } from 'react-router-dom'

export function LoginPage() {
	const { login, isLoading } = authStore()
	const navigate = useNavigate()
	const location = useLocation() as unknown as { state?: { from?: { pathname?: string } } }
	const [email, setEmail] = useState('')
	const [password, setPassword] = useState('')

	async function onSubmit(e: FormEvent) {
		e.preventDefault()
		try {
			await login(email, password)
			navigate(location.state?.from?.pathname || '/dashboard', { replace: true })
		} catch {
			alert('Login failed')
		}
	}

	return (
		<div className="min-h-screen flex items-center justify-center">
			<form onSubmit={onSubmit} className="w-full max-w-sm space-y-4 p-6 rounded-lg border">
				<h1 className="text-xl font-semibold">Sign in</h1>
				<input
					type="email"
					value={email}
					onChange={(e) => setEmail(e.target.value)}
					placeholder="Email"
					className="w-full px-3 py-2 rounded-md border"
					required
				/>
				<input
					type="password"
					value={password}
					onChange={(e) => setPassword(e.target.value)}
					placeholder="Password"
					className="w-full px-3 py-2 rounded-md border"
					required
				/>
				<button disabled={isLoading} className="w-full py-2 rounded-md bg-gray-900 text-white">
					{isLoading ? 'Signing in...' : 'Sign in'}
				</button>
				<p className="text-sm">
					No account? <Link to="/register" className="underline">Create one</Link>
				</p>
			</form>
		</div>
	)
}