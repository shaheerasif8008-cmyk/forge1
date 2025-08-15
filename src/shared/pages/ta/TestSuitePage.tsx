import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../../lib/api'

interface TestParams { duration: number; concurrency: number; dataset: string }
interface Suite { id: string; name: string; description: string }
interface Run { id: string; suiteId: string; params: TestParams; startedAt: string; status: 'running'|'completed'|'failed' }

export function TestSuitePage() {
	const [suites, setSuites] = useState<Suite[]>([])
	const [params, setParams] = useState<TestParams>({ duration: 10, concurrency: 2, dataset: 'default' })
	const [selected, setSelected] = useState<string>('')
	const [saving, setSaving] = useState(false)
	const [runs, setRuns] = useState<Run[]>(() => JSON.parse(localStorage.getItem('forge1-runs') || '[]'))

	useEffect(() => { localStorage.setItem('forge1-runs', JSON.stringify(runs)) }, [runs])

	useEffect(() => {
		async function load() {
			try {
				const { data } = await api.get('/testing/suites')
				setSuites(data)
			} catch {}
		}
		load()
	}, [])

	async function start() {
		if (!selected) return toast.error('Select a suite')
		setSaving(true)
		try {
			const { data } = await api.post(`/testing/suites/${selected}/start`, params)
			const run: Run = { id: data?.runId || crypto.randomUUID(), suiteId: selected, params, startedAt: new Date().toISOString(), status: 'running' }
			setRuns([run, ...runs])
			toast.success('Test started')
		} catch (e: any) {
			toast.error(e?.response?.data?.message || 'Failed to start')
		} finally {
			setSaving(false)
		}
	}

	return (
		<div className="space-y-6">
			<h1 className="text-xl font-semibold tracking-tight">Test Suite Selector</h1>
			<div className="grid md:grid-cols-2 gap-4">
				<div className="rounded-lg border p-4 space-y-3">
					<div>
						<label className="text-sm" htmlFor="suite">Suite</label>
						<select id="suite" className="w-full rounded-md border px-3 py-2" value={selected} onChange={e=>setSelected(e.target.value)}>
							<option value="">Select a suite</option>
							{suites.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
						</select>
					</div>
					<div className="grid grid-cols-3 gap-3">
						<div>
							<label className="text-sm" htmlFor="duration">Duration (min)</label>
							<input id="duration" type="number" className="w-full rounded-md border px-3 py-2" value={params.duration} onChange={e=>setParams({...params, duration: Number(e.target.value)})} />
						</div>
						<div>
							<label className="text-sm" htmlFor="concurrency">Concurrency</label>
							<input id="concurrency" type="number" className="w-full rounded-md border px-3 py-2" value={params.concurrency} onChange={e=>setParams({...params, concurrency: Number(e.target.value)})} />
						</div>
						<div>
							<label className="text-sm" htmlFor="dataset">Dataset</label>
							<input id="dataset" className="w-full rounded-md border px-3 py-2" value={params.dataset} onChange={e=>setParams({...params, dataset: e.target.value})} />
						</div>
					</div>
					<div className="flex justify-end">
						<button className="rounded-md border px-3 py-2 disabled:opacity-50" onClick={start} disabled={saving}>{saving ? 'Starting…' : 'Start Test'}</button>
					</div>
				</div>
				<div className="rounded-lg border p-4">
					<div className="text-sm text-muted-foreground mb-2">Recent Runs</div>
					<div className="space-y-2 text-sm">
						{runs.length === 0 && <div className="text-muted-foreground">No runs yet</div>}
						{runs.map(r => (
							<div key={r.id} className="flex items-center justify-between border rounded-md px-3 py-2">
								<div>
									<div className="font-medium">{suites.find(s=>s.id===r.suiteId)?.name || r.suiteId}</div>
									<div className="text-muted-foreground">{new Date(r.startedAt).toLocaleString()} • {r.params.duration}m • c={r.params.concurrency}</div>
								</div>
								<div className={`text-xs rounded-full border px-2 py-0.5 ${r.status==='running'?'bg-blue-500/10 text-blue-600 border-blue-600/30': r.status==='completed'?'bg-green-500/10 text-green-600 border-green-600/30':'bg-rose-500/10 text-rose-600 border-rose-600/30'}`}>
									{r.status}
								</div>
							</div>
						))}
					</div>
				</div>
			</div>
		</div>
	)
}
