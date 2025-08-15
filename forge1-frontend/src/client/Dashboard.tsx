export function DashboardPage() {
	return (
		<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
			<div className="p-4 border rounded-lg">
				<div className="text-sm text-gray-500">Active Employees</div>
				<div className="text-2xl font-semibold">--</div>
			</div>
			<div className="p-4 border rounded-lg">
				<div className="text-sm text-gray-500">Monthly Usage</div>
				<div className="text-2xl font-semibold">--</div>
			</div>
			<div className="p-4 border rounded-lg">
				<div className="text-sm text-gray-500">Billing Status</div>
				<div className="text-2xl font-semibold">--</div>
			</div>
		</div>
	)
}