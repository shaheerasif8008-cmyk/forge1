export function EmployeeBuilderPage() {
	return (
		<div className="space-y-4">
			<h2 className="text-lg font-semibold">Employee Builder</h2>
			<div className="grid md:grid-cols-3 gap-4">
				<div className="p-4 border rounded-lg">1. Basics</div>
				<div className="p-4 border rounded-lg">2. Skills</div>
				<div className="p-4 border rounded-lg">3. Deployment</div>
			</div>
			<div className="flex justify-end">
				<button className="px-3 py-2 rounded-md bg-gray-900 text-white">Save</button>
			</div>
		</div>
	)
}