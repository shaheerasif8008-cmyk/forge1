import type { FormEvent } from 'react'
import { useState } from 'react'
import { authStore } from '../stores/auth'
import { useNavigate, Link } from 'react-router-dom'

export function RegisterPage() {
	const { register, isLoading } = authStore()
	const navigate = useNavigate()
	const [name, setName] = useState('')
	const [email, setEmail] = useState('')
	const [password, setPassword] = useState('')

	async function onSubmit(e: FormEvent) {
		e.preventDefault()
		try {
			await register(email, password, name)
			navigate('/dashboard', { replace: true })
		} catch {
			alert('Register failed')
		}
	}

	return (
		<div className="min-h-screen flex items-center justify-center">
			<form onSubmit={onSubmit} className="w-full max-w-sm space-y-4 p-6 rounded-lg border">
				<h1 className="text-xl font-semibold">Create account</h1>
				<input
					value={name}
					onChange={(e) => setName(e.target.value)}
					placeholder="Name"
					className="w-full px-3 py-2 rounded-md border"
				/>
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
					{isLoading ? 'Creating...' : 'Create account'}
				</button>
				<p className="text-sm">
					Have an account? <Link to="/login" className="underline">Sign in</Link>
				</p>
			</form>
		</div>
	)
}