import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, Area } from 'recharts'

export function PerformancePage() {
	const [data, setData] = useState<any>({ metrics: [] })
	useEffect(() => {
		let mounted = true
		async function load() {
			try {
				const { data } = await api.get('/testing/performance')
				if (mounted) setData(data)
			} catch {}
		}
		load()
		const id = setInterval(load, 5000)
		return () => { mounted = false; clearInterval(id) }
	}, [])

	return (
		<div className="space-y-6">
			<h1 className="text-xl font-semibold tracking-tight">Performance Dashboard</h1>
			<div className="grid md:grid-cols-2 gap-4">
				<div className="rounded-lg border p-4">
					<div className="text-sm text-muted-foreground mb-2">CPU %</div>
					<div className="h-56">
						<ResponsiveContainer width="100%" height="100%">
							<LineChart data={data.metrics}>
								<CartesianGrid strokeDasharray="3 3" />
								<XAxis dataKey="t" hide />
								<YAxis domain={[0, 100]} />
								<Tooltip />
								<Line type="monotone" dataKey="cpu" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
							</LineChart>
						</ResponsiveContainer>
					</div>
				</div>
				<div className="rounded-lg border p-4">
					<div className="text-sm text-muted-foreground mb-2">Memory %</div>
					<div className="h-56">
						<ResponsiveContainer width="100%" height="100%">
							<AreaChart data={data.metrics}>
								<CartesianGrid strokeDasharray="3 3" />
								<XAxis dataKey="t" hide />
								<YAxis domain={[0, 100]} />
								<Tooltip />
								<Area type="monotone" dataKey="mem" fill="hsl(var(--accent))" stroke="hsl(var(--accent))" />
							</AreaChart>
						</ResponsiveContainer>
					</div>
				</div>
				<div className="rounded-lg border p-4">
					<div className="text-sm text-muted-foreground mb-2">API Latency (ms)</div>
					<div className="h-56">
						<ResponsiveContainer width="100%" height="100%">
							<LineChart data={data.metrics}>
								<CartesianGrid strokeDasharray="3 3" />
								<XAxis dataKey="t" hide />
								<YAxis />
								<Tooltip />
								<Line type="monotone" dataKey="latency" stroke="hsl(var(--destructive))" strokeWidth={2} dot={false} />
							</LineChart>
						</ResponsiveContainer>
					</div>
				</div>
				<div className="rounded-lg border p-4">
					<div className="text-sm text-muted-foreground mb-2">Success Rate %</div>
					<div className="h-56">
						<ResponsiveContainer width="100%" height="100%">
							<LineChart data={data.metrics}>
								<CartesianGrid strokeDasharray="3 3" />
								<XAxis dataKey="t" hide />
								<YAxis domain={[0, 100]} />
								<Tooltip />
								<Line type="monotone" dataKey="success" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
							</LineChart>
						</ResponsiveContainer>
					</div>
				</div>
			</div>
		</div>
	)
}