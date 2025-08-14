import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'

export function LoginPage() {
	const navigate = useNavigate()
	const location = useLocation() as any
	const from = location.state?.from?.pathname || '/cp'
	const login = useAuthStore(s => s.login)
	const [email, setEmail] = useState('')
	const [password, setPassword] = useState('')
	const [loading, setLoading] = useState(false)

	async function onSubmit(e: React.FormEvent) {
		e.preventDefault()
		if (!email || !password) return toast.error('Enter email and password')
		setLoading(true)
		try {
			const { data } = await api.post('/auth/login', { email, password })
			if (!data?.token) throw new Error('Invalid response')
			login(data.token, email)
			toast.success('Logged in')
			navigate(from, { replace: true })
		} catch (err: any) {
			toast.error(err?.response?.data?.message || 'Login failed')
		} finally {
			setLoading(false)
		}
	}

	return (
		<div className="mx-auto max-w-md py-12">
			<h1 className="text-2xl font-semibold tracking-tight mb-6">Sign in</h1>
			<form onSubmit={onSubmit} className="space-y-4">
				<div className="space-y-2">
					<label className="text-sm" htmlFor="email">Email</label>
					<input
						id="email"
						type="email"
						className="w-full rounded-md border bg-background px-3 py-2"
						value={email}
						onChange={(e)=>setEmail(e.target.value)}
						required
					/>
				</div>
				<div className="space-y-2">
					<label className="text-sm" htmlFor="password">Password</label>
					<input
						id="password"
						type="password"
						className="w-full rounded-md border bg-background px-3 py-2"
						value={password}
						onChange={(e)=>setPassword(e.target.value)}
						required
					/>
				</div>
				<button
					type="submit"
					disabled={loading}
					className="w-full rounded-md border px-3 py-2 font-medium hover:bg-accent disabled:opacity-50"
				>
					{loading ? 'Signing in…' : 'Sign in'}
				</button>
			</form>
			<p className="text-sm text-muted-foreground mt-4">No account? <Link className="underline" to="/register">Register</Link></p>
		</div>
	)
}