import { Outlet, Link, NavLink, useLocation } from 'react-router-dom'
import { Moon, Sun, LayoutDashboard, Users, Settings, CreditCard, Wrench, BarChart3, FileText, LogOut } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useAuthStore } from '../stores/authStore'

export function AppLayout() {
	const location = useLocation()
	const [isDark, setIsDark] = useState(() => document.documentElement.classList.contains('dark'))
	const [sidebarOpen, setSidebarOpen] = useState(false)
	const logout = useAuthStore(s => s.logout)
	const isAuthenticated = useAuthStore(s => s.isAuthenticated)

	useEffect(() => {
		if (isDark) document.documentElement.classList.add('dark')
		else document.documentElement.classList.remove('dark')
		localStorage.setItem('theme', isDark ? 'dark' : 'light')
	}, [isDark])

	useEffect(() => {
		const saved = localStorage.getItem('theme')
		if (saved) setIsDark(saved === 'dark')
	}, [])

	const activeClass = 'bg-accent text-accent-foreground'
	const baseItem = 'flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent hover:text-accent-foreground transition-colors'

	return (
		<div className="min-h-screen grid grid-cols-[260px_1fr] grid-rows-[56px_1fr]">
			<header className="col-span-2 row-start-1 flex items-center justify-between px-4 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 h-14">
				<div className="flex items-center gap-3">
					<button className="md:hidden inline-flex items-center justify-center rounded-md border h-8 w-8" 		onClick={() => { setSidebarOpen(v=>!v); document.documentElement.classList.toggle('sidebar-open') }} aria-label="Toggle sidebar">
						<span className="sr-only">Toggle sidebar</span>
						☰
					</button>
					<Link to="/cp" className="font-semibold tracking-tight">Forge1</Link>
				</div>
				<div className="flex items-center gap-3">
					<button
						className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm"
						onClick={() => setIsDark(v => !v)}
						aria-label="Toggle theme"
					>
						{isDark ? <Sun size={16} /> : <Moon size={16} />}
						<span className="hidden sm:inline">{isDark ? 'Light' : 'Dark'}</span>
					</button>
					{isAuthenticated && (
						<button
							className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm"
							onClick={logout}
						>
							<LogOut size={16} />
							<span className="hidden sm:inline">Logout</span>
						</button>
					)}
				</div>
			</header>

			<aside className="row-start-2 border-r p-3 hidden md:block md:static fixed inset-y-14 left-0 z-40 w-[260px] bg-background transition-transform md:translate-x-0 translate-x-[-100%] [html.sidebar-open_&]:translate-x-0">
				<nav className="space-y-2 text-sm">
					<div className="uppercase text-muted-foreground px-2">Client Portal</div>
					<NavLink to="/cp" className={({isActive}) => `${baseItem} ${isActive ? activeClass : ''}`}>
						<LayoutDashboard size={16} /> Dashboard
					</NavLink>
					<NavLink to="/cp/employees" className={({isActive}) => `${baseItem} ${isActive ? activeClass : ''}`}>
						<Users size={16} /> Employees
					</NavLink>
					<NavLink to="/cp/builder" className={({isActive}) => `${baseItem} ${isActive ? activeClass : ''}`}>
						<Wrench size={16} /> Builder
					</NavLink>
					<NavLink to="/cp/billing" className={({isActive}) => `${baseItem} ${isActive ? activeClass : ''}`}>
						<CreditCard size={16} /> Billing
					</NavLink>
					<NavLink to="/cp/settings" className={({isActive}) => `${baseItem} ${isActive ? activeClass : ''}`}>
						<Settings size={16} /> Settings
					</NavLink>

					<div className="uppercase text-muted-foreground px-2 pt-4">Testing App</div>
					<NavLink to="/ta" className={({isActive}) => `${baseItem} ${isActive ? activeClass : ''}`}>
						<Wrench size={16} /> Test Suites
					</NavLink>
					<NavLink to="/ta/live" className={({isActive}) => `${baseItem} ${isActive ? activeClass : ''}`}>
						<FileText size={16} /> Live Monitor
					</NavLink>
					<NavLink to="/ta/performance" className={({isActive}) => `${baseItem} ${isActive ? activeClass : ''}`}>
						<BarChart3 size={16} /> Performance
					</NavLink>
					<NavLink to="/ta/reports" className={({isActive}) => `${baseItem} ${isActive ? activeClass : ''}`}>
						<FileText size={16} /> Reports
					</NavLink>
				</nav>
			</aside>

			<main className="row-start-2 col-start-2 p-4">
				<Outlet />
			</main>
		</div>
	)
}