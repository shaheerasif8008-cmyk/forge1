import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AppShell } from './components/layout/AppShell'
import { LoginPage } from './client/Login'
import { RegisterPage } from './client/Register'
import { DashboardPage } from './client/Dashboard'
import { EmployeesPage } from './client/Employees'
import { EmployeeBuilderPage } from './client/EmployeeBuilder'
import { BillingPage } from './client/Billing'
import { SettingsPage } from './client/Settings'
import { ProfilePage } from './client/Profile'
import { TestSuiteSelectorPage } from './testing/TestSuiteSelector'
import { LiveMonitorPage } from './testing/LiveMonitor'
import { PerformanceDashboardPage } from './testing/PerformanceDashboard'
import { ReportsPage } from './testing/Reports'
import { ProtectedRoute } from './routes/ProtectedRoute'

function App() {
	return (
		<BrowserRouter>
			<Toaster position="top-right" />
			<Routes>
				<Route path="/login" element={<LoginPage />} />
				<Route path="/register" element={<RegisterPage />} />

				<Route
					path="/"
					element={
						<ProtectedRoute>
							<AppShell />
						</ProtectedRoute>
					}
				>
					<Route index element={<Navigate to="/dashboard" replace />} />
					<Route path="/dashboard" element={<DashboardPage />} />
					<Route path="/employees" element={<EmployeesPage />} />
					<Route path="/builder" element={<EmployeeBuilderPage />} />
					<Route path="/billing" element={<BillingPage />} />
					<Route path="/settings" element={<SettingsPage />} />
					<Route path="/profile" element={<ProfilePage />} />

					{/* Testing App */}
					<Route path="/testing" element={<TestSuiteSelectorPage />} />
					<Route path="/testing/live" element={<LiveMonitorPage />} />
					<Route path="/testing/perf" element={<PerformanceDashboardPage />} />
					<Route path="/testing/reports" element={<ReportsPage />} />
				</Route>

				<Route path="*" element={<Navigate to="/dashboard" replace />} />
			</Routes>
		</BrowserRouter>
	)
}

export default App
