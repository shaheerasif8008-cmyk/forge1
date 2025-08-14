import { useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../../lib/api'

export function BuilderPage() {
	const [step, setStep] = useState(1)
	const [form, setForm] = useState({ name: '', role: '', description: '', config: '' })
	const [loading, setLoading] = useState(false)

	function next() { setStep(s => Math.min(3, s + 1)) }
	function prev() { setStep(s => Math.max(1, s - 1)) }

	async function create() {
		if (!form.name || !form.role) return toast.error('Name and role are required')
		setLoading(true)
		try {
			await api.post('/employees', form)
			toast.success('Employee created')
			setForm({ name: '', role: '', description: '', config: '' })
			setStep(1)
		} catch (e: any) {
			toast.error(e?.response?.data?.message || 'Creation failed')
		} finally {
			setLoading(false)
		}
	}

	return (
		<div className="space-y-6">
			<h1 className="text-xl font-semibold tracking-tight">Employee Builder</h1>
			<div className="flex items-center gap-2 text-sm">
				{[1,2,3].map(n => (
					<div key={n} className={`px-2 py-1 rounded border ${step===n?'bg-primary text-primary-foreground':'text-muted-foreground'}`}>Step {n}</div>
				))}
			</div>
			<div className="rounded-lg border p-4 space-y-4">
				{step === 1 && (
					<div className="grid gap-4 md:grid-cols-2">
						<div>
							<label className="text-sm" htmlFor="name">Name</label>
							<input id="name" className="w-full rounded-md border px-3 py-2" value={form.name} onChange={e=>setForm({...form, name: e.target.value})} />
						</div>
						<div>
							<label className="text-sm" htmlFor="role">Role</label>
							<input id="role" className="w-full rounded-md border px-3 py-2" value={form.role} onChange={e=>setForm({...form, role: e.target.value})} />
						</div>
						<div className="md:col-span-2">
							<label className="text-sm" htmlFor="desc">Description</label>
							<textarea id="desc" className="w-full rounded-md border px-3 py-2 min-h-24" value={form.description} onChange={e=>setForm({...form, description: e.target.value})} />
						</div>
					</div>
				)}
				{step === 2 && (
					<div>
						<label className="text-sm" htmlFor="config">Configuration (JSON)</label>
						<textarea id="config" className="w-full rounded-md border px-3 py-2 min-h-56 font-mono" placeholder='{"concurrency":2,"dataset":"default"}' value={form.config} onChange={e=>setForm({...form, config: e.target.value})} />
					</div>
				)}
				{step === 3 && (
					<div className="space-y-2 text-sm">
						<div><span className="text-muted-foreground">Name:</span> {form.name || '—'}</div>
						<div><span className="text-muted-foreground">Role:</span> {form.role || '—'}</div>
						<div><span className="text-muted-foreground">Description:</span> {form.description || '—'}</div>
						<div><span className="text-muted-foreground">Config:</span> <pre className="mt-2 rounded bg-muted p-2 overflow-auto max-h-48">{form.config || '—'}</pre></div>
					</div>
				)}
				<div className="flex items-center justify-between pt-4">
					<button className="rounded-md border px-3 py-2 disabled:opacity-50" onClick={prev} disabled={step===1}>Back</button>
					{step < 3 ? (
						<button className="rounded-md border px-3 py-2" onClick={next}>Next</button>
					) : (
						<button className="rounded-md border px-3 py-2 disabled:opacity-50" onClick={create} disabled={loading}>{loading ? 'Creating…' : 'Create Employee'}</button>
					)}
				</div>
			</div>
		</div>
	)
}