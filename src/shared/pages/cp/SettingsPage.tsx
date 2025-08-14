import { useState } from 'react'

export function SettingsPage() {
	const [name, setName] = useState('')
	const [company, setCompany] = useState('')
	const [saving, setSaving] = useState(false)

	return (
		<div className="space-y-6">
			<h1 className="text-xl font-semibold tracking-tight">Settings & Profile</h1>
			<div className="rounded-lg border p-4 space-y-4">
				<div className="grid md:grid-cols-2 gap-4">
					<div>
						<label className="text-sm" htmlFor="name">Name</label>
						<input id="name" className="w-full rounded-md border px-3 py-2" value={name} onChange={e=>setName(e.target.value)} />
					</div>
					<div>
						<label className="text-sm" htmlFor="company">Company</label>
						<input id="company" className="w-full rounded-md border px-3 py-2" value={company} onChange={e=>setCompany(e.target.value)} />
					</div>
				</div>
				<div className="flex justify-end">
					<button className="rounded-md border px-3 py-2 disabled:opacity-50" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
				</div>
			</div>
			<p className="text-sm text-muted-foreground">Use the header toggle to switch between dark and light mode.</p>
		</div>
	)
}