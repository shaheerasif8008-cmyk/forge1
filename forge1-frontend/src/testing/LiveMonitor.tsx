import { useEffect, useState } from 'react'

export function LiveMonitorPage() {
	const [logs, setLogs] = useState<string[]>([])

	useEffect(() => {
		// Initialize with a placeholder to avoid unused warnings before SSE wiring
		setLogs(['SSE connection pending...'])
		// SSE placeholder - wire actual endpoint when ready
		// const es = new EventSource(`${import.meta.env.VITE_API_BASE_URL}/api/v1/testing/stream`)
		// es.onmessage = (e) => setLogs((prev) => [...prev, e.data])
		// return () => es.close()
	}, [])

	return (
		<div className="space-y-4">
			<h2 className="text-lg font-semibold">Live Test Monitor</h2>
			<div className="p-4 border rounded-lg h-[60vh] overflow-auto font-mono text-xs whitespace-pre-wrap">
				{logs.length === 0 ? 'No logs yet' : logs.join('\n')}
			</div>
		</div>
	)
}