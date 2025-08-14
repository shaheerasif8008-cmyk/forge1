export function TestSuiteSelectorPage() {
	return (
		<div className="space-y-4">
			<h2 className="text-lg font-semibold">Test Suites</h2>
			<div className="grid md:grid-cols-3 gap-4">
				<button className="p-4 border rounded-lg text-left">Smoke Tests</button>
				<button className="p-4 border rounded-lg text-left">Load Tests</button>
				<button className="p-4 border rounded-lg text-left">Regression</button>
			</div>
		</div>
	)
}