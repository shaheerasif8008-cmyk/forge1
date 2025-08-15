import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const sample = Array.from({ length: 12 }).map((_, i) => ({
	name: `t${i}`,
	cpu: Math.round(20 + Math.random() * 60),
	mem: Math.round(30 + Math.random() * 50),
	latency: Math.round(100 + Math.random() * 200),
}))

export function PerformanceDashboardPage() {
	return (
		<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
			<div className="p-4 border rounded-lg">
				<div className="mb-2 font-medium">CPU %</div>
				<div className="h-56">
					<ResponsiveContainer width="100%" height="100%">
						<LineChart data={sample}>
							<CartesianGrid strokeDasharray="3 3" />
							<XAxis dataKey="name" />
							<YAxis />
							<Tooltip />
							<Line type="monotone" dataKey="cpu" stroke="#111827" dot={false} />
						</LineChart>
					</ResponsiveContainer>
				</div>
			</div>
			<div className="p-4 border rounded-lg">
				<div className="mb-2 font-medium">Latency (ms)</div>
				<div className="h-56">
					<ResponsiveContainer width="100%" height="100%">
						<LineChart data={sample}>
							<CartesianGrid strokeDasharray="3 3" />
							<XAxis dataKey="name" />
							<YAxis />
							<Tooltip />
							<Line type="monotone" dataKey="latency" stroke="#2563eb" dot={false} />
						</LineChart>
					</ResponsiveContainer>
				</div>
			</div>
		</div>
	)
}