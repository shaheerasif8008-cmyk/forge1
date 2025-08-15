import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '../../lib/api'

export function RegisterPage() {
	const navigate = useNavigate()
	const [email, setEmail] = useState('')
	const [password, setPassword] = useState('')
	const [name, setName] = useState('')
	const [loading, setLoading] = useState(false)

	async function onSubmit(e: React.FormEvent) {
		e.preventDefault()
		if (!email || !password || !name) return toast.error('Fill all fields')
		setLoading(true)
		try {
			await api.post('/auth/register', { email, password, name })
			toast.success('Registered. Please login.')
			navigate('/login')
		} catch (err: any) {
			toast.error(err?.response?.data?.message || 'Registration failed')
		} finally {
			setLoading(false)
		}
	}

	return (
		<div className="mx-auto max-w-md py-12">
			<h1 className="text-2xl font-semibold tracking-tight mb-6">Create account</h1>
			<form onSubmit={onSubmit} className="space-y-4">
				<div className="space-y-2">
					<label className="text-sm" htmlFor="name">Name</label>
					<input
						id="name"
						type="text"
						className="w-full rounded-md border bg-background px-3 py-2"
						value={name}
						onChange={(e)=>setName(e.target.value)}
						required
					/>
				</div>
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
					{loading ? 'Creating…' : 'Create account'}
				</button>
			</form>
			<p className="text-sm text-muted-foreground mt-4">Have an account? <Link className="underline" to="/login">Sign in</Link></p>
		</div>
	)
}
