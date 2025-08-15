import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { authStore } from '../../stores/auth'

export function AppShell() {
	const navigate = useNavigate()
	const { user, logout } = authStore()

	return (
		<div className="min-h-screen flex bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100">
			<aside className="w-64 shrink-0 border-r border-gray-200 dark:border-gray-800 p-4 space-y-2 hidden md:block">
				<div className="text-xl font-semibold mb-4">Forge1</div>
				<nav className="flex flex-col gap-1">
					<NavLink to="/dashboard" className={({ isActive }) => linkClasses(isActive)}>Dashboard</NavLink>
					<NavLink to="/employees" className={({ isActive }) => linkClasses(isActive)}>Employees</NavLink>
					<NavLink to="/builder" className={({ isActive }) => linkClasses(isActive)}>Employee Builder</NavLink>
					<NavLink to="/billing" className={({ isActive }) => linkClasses(isActive)}>Billing</NavLink>
					<NavLink to="/settings" className={({ isActive }) => linkClasses(isActive)}>Settings</NavLink>
					<NavLink to="/profile" className={({ isActive }) => linkClasses(isActive)}>Profile</NavLink>
					<div className="mt-4 text-xs uppercase tracking-wide text-gray-500">Testing</div>
					<NavLink to="/testing" className={({ isActive }) => linkClasses(isActive)}>Test Suites</NavLink>
					<NavLink to="/testing/live" className={({ isActive }) => linkClasses(isActive)}>Live Monitor</NavLink>
					<NavLink to="/testing/perf" className={({ isActive }) => linkClasses(isActive)}>Performance</NavLink>
					<NavLink to="/testing/reports" className={({ isActive }) => linkClasses(isActive)}>Reports</NavLink>
				</nav>
			</aside>
			<div className="flex-1 flex flex-col min-w-0">
				<header className="h-14 border-b border-gray-200 dark:border-gray-800 px-4 flex items-center justify-between">
					<div className="md:hidden font-semibold">Forge1</div>
					<div className="flex items-center gap-3">
						<span className="text-sm text-gray-600 dark:text-gray-300">{user?.email}</span>
						<button
							className="px-3 py-1.5 rounded-md bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900 text-sm"
							onClick={() => {
								logout()
								navigate('/login')
							}}
						>
							Logout
						</button>
					</div>
				</header>
				<main className="p-4 min-w-0">
					<Outlet />
				</main>
			</div>
		</div>
	)
}

function linkClasses(isActive: boolean) {
	return (
		'px-3 py-2 rounded-md text-sm font-medium ' +
		(isActive
			? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
			: 'hover:bg-gray-100 dark:hover:bg-gray-800')
	)
}