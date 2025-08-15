import { authStore } from '../stores/auth'

export function ProfilePage() {
	const { user } = authStore()
	return (
		<div className="space-y-4">
			<h2 className="text-lg font-semibold">Profile</h2>
			<div className="p-4 border rounded-lg">
				<div>Email: {user?.email}</div>
				<div>Name: {user?.name || '—'}</div>
				<div>Role: {user?.role || 'client'}</div>
			</div>
		</div>
	)
}