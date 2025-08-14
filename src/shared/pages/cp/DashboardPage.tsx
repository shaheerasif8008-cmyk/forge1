import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'

export function DashboardPage() {
	const [loading, setLoading] = useState(true)
	const [stats, setStats] = useState<any>(null)

	useEffect(() => {
		let mounted = true
		async function load() {
			try {
				const { data } = await api.get('/cp/overview')
				if (mounted) setStats(data)
			} catch (e) {
				// silently fail for skeleton demo
			} finally {
				if (mounted) setLoading(false)
			}
		}
		load()
		return () => { mounted = false }
	}, [])

	return (
		<div className="space-y-6">
			<h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				{['Employees', 'Active Jobs', 'Monthly Spend'].map((label, idx) => (
					<div key={idx} className="rounded-lg border p-4">
						<div className="text-sm text-muted-foreground">{label}</div>
						<div className="text-2xl font-semibold mt-2">{loading ? '—' : stats?.cards?.[idx] ?? '0'}</div>
					</div>
				))}
			</div>
			<div className="rounded-lg border p-4">
				<div className="text-sm text-muted-foreground mb-2">Performance</div>
				<div className="h-64">
					<ResponsiveContainer width="100%" height="100%">
						<LineChart data={stats?.chart ?? []}>
							<CartesianGrid strokeDasharray="3 3" />
							<XAxis dataKey="t" />
							<YAxis />
							<Tooltip />
							<Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
						</LineChart>
					</ResponsiveContainer>
				</div>
			</div>
		</div>
	)
}