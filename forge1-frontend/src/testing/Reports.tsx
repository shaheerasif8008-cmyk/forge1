import { useState } from 'react'

export function ReportsPage() {
	const [src, setSrc] = useState<string>('')
	return (
		<div className="space-y-4">
			<h2 className="text-lg font-semibold">Result Reports</h2>
			<div className="flex gap-2">
				<input
					placeholder="Report URL (HTML/PDF)"
					value={src}
					onChange={(e) => setSrc(e.target.value)}
					className="flex-1 px-3 py-2 rounded-md border"
				/>
				<button className="px-3 py-2 rounded-md bg-gray-900 text-white">Load</button>
			</div>
			<div className="border rounded-lg h-[70vh] overflow-hidden">
				{src ? (
					<iframe src={src} className="w-full h-full" />
				) : (
					<div className="h-full flex items-center justify-center text-sm text-gray-600">Enter a report URL to view</div>
				)}
			</div>
		</div>
	)
}