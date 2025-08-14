import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppLayout } from './shared/layouts/AppLayout'
import { LoginPage } from './shared/pages/auth/LoginPage'
import { RegisterPage } from './shared/pages/auth/RegisterPage'
import { DashboardPage } from './shared/pages/cp/DashboardPage'
import { EmployeesPage } from './shared/pages/cp/EmployeesPage'
import { BuilderPage } from './shared/pages/cp/BuilderPage'
import { BillingPage } from './shared/pages/cp/BillingPage'
import { SettingsPage } from './shared/pages/cp/SettingsPage'
import { TestSuitePage } from './shared/pages/ta/TestSuitePage'
import { LiveMonitorPage } from './shared/pages/ta/LiveMonitorPage'
import { PerformancePage } from './shared/pages/ta/PerformancePage'
import { ReportsPage } from './shared/pages/ta/ReportsPage'
import { ProtectedRoute } from './shared/routes/ProtectedRoute'

export const router = createBrowserRouter([
	{
		path: '/',
		element: <Navigate to="/cp" replace />,
	},
	{
		path: '/',
		element: <AppLayout />,
		children: [
			{ path: 'login', element: <LoginPage /> },
			{ path: 'register', element: <RegisterPage /> },
			{
				path: 'cp',
				element: (
					<ProtectedRoute>
						<DashboardPage />
					</ProtectedRoute>
				),
			},
			{
				path: 'cp/employees',
				element: (
					<ProtectedRoute>
						<EmployeesPage />
					</ProtectedRoute>
				),
			},
			{
				path: 'cp/builder',
				element: (
					<ProtectedRoute>
						<BuilderPage />
					</ProtectedRoute>
				),
			},
			{
				path: 'cp/billing',
				element: (
					<ProtectedRoute>
						<BillingPage />
					</ProtectedRoute>
				),
			},
			{
				path: 'cp/settings',
				element: (
					<ProtectedRoute>
						<SettingsPage />
					</ProtectedRoute>
				),
			},
			{
				path: 'ta',
				element: (
					<ProtectedRoute>
						<TestSuitePage />
					</ProtectedRoute>
				),
			},
			{
				path: 'ta/live',
				element: (
					<ProtectedRoute>
						<LiveMonitorPage />
					</ProtectedRoute>
				),
			},
			{
				path: 'ta/performance',
				element: (
					<ProtectedRoute>
						<PerformancePage />
					</ProtectedRoute>
				),
			},
			{
				path: 'ta/reports',
				element: (
					<ProtectedRoute>
						<ReportsPage />
					</ProtectedRoute>
				),
			},
		],
	},
	{ path: '*', element: <Navigate to="/cp" replace /> },
])