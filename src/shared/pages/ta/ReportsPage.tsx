import { useState } from 'react'

export function ReportsPage() {
	const [url, setUrl] = useState('')
	const isPdf = url.toLowerCase().endsWith('.pdf')
	return (
		<div className="space-y-4">
			<h1 className="text-xl font-semibold tracking-tight">Result Reports</h1>
			<div className="flex gap-2">
				<input className="flex-1 rounded-md border px-3 py-2" placeholder="Paste a report URL (HTML/PDF)" value={url} onChange={e=>setUrl(e.target.value)} />
				<button className="rounded-md border px-3 py-2 hover:bg-accent" onClick={()=>setUrl(url)}>Load</button>
			</div>
			<div className="rounded-lg border overflow-hidden min-h-[70vh]">
				{url ? (
					isPdf ? (
						<object data={url} type="application/pdf" className="w-full h-[80vh]">
							<iframe src={url} className="w-full h-full" />
						</object>
					) : (
						<iframe src={url} className="w-full h-[80vh]" />
					)
				) : (
					<div className="p-6 text-sm text-muted-foreground">Enter a report URL to preview</div>
				)}
			</div>
		</div>
	)
}
