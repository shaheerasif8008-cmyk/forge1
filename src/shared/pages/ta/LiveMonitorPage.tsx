import { useEffect, useRef, useState } from 'react'
import { api } from '../../lib/api'

interface LogEvent { id: string; ts: string; level: 'info'|'warn'|'error'; message: string }

export function LiveMonitorPage() {
	const [events, setEvents] = useState<LogEvent[]>([])
	const [polling, setPolling] = useState(false)
	const endRef = useRef<HTMLDivElement | null>(null)

	useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [events])

	useEffect(() => {
		let isMounted = true
		setPolling(true)
		const interval = setInterval(async () => {
			try {
				const { data } = await api.get('/testing/logs?limit=50')
				if (isMounted) setEvents(data)
			} catch {}
		}, 2000)
		return () => { isMounted = false; clearInterval(interval); setPolling(false) }
	}, [])

	return (
		<div className="space-y-4">
			<h1 className="text-xl font-semibold tracking-tight">Live Test Monitor</h1>
			<div className="rounded-lg border p-4 h-[60vh] overflow-auto bg-card">
				{events.map(ev => (
					<div key={ev.id} className="text-xs font-mono">
						<span className="text-muted-foreground">{new Date(ev.ts).toLocaleTimeString()}</span>
						<span className={`ml-2 uppercase ${ev.level==='error'?'text-rose-600':ev.level==='warn'?'text-amber-600':'text-green-600'}`}>{ev.level}</span>
						<span className="ml-2">{ev.message}</span>
					</div>
				))}
				<div ref={endRef} />
			</div>
			<div className="text-sm text-muted-foreground">{polling ? 'Polling every 2s (SSE under testing)…' : 'Stopped'}</div>
		</div>
	)
}
