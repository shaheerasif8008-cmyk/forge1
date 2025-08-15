import { useEffect, useState } from 'react'
import { listEmployees, startEmployee, stopEmployee, type Employee } from '../services/employees'

export function EmployeesPage() {
	const [items, setItems] = useState<Employee[]>([])
	const [loading, setLoading] = useState(true)

	async function refresh() {
		setLoading(true)
		try {
			const data = await listEmployees()
			setItems(data)
		} catch {
			setItems([])
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		refresh()
	}, [])

	return (
		<div className="space-y-4">
			<div className="flex items-center justify-between">
				<h2 className="text-lg font-semibold">AI Employees</h2>
				<button className="px-3 py-2 rounded-md bg-gray-900 text-white">New Employee</button>
			</div>
			<div className="overflow-x-auto border rounded-lg">
				<table className="w-full text-sm">
					<thead className="bg-gray-50 dark:bg-gray-800">
						<tr>
							<th className="text-left p-3">Name</th>
							<th className="text-left p-3">Status</th>
							<th className="text-left p-3">Last Update</th>
							<th className="text-right p-3">Actions</th>
						</tr>
					</thead>
					<tbody>
						{loading && (
							<tr>
								<td className="p-3" colSpan={4}>Loading...</td>
							</tr>
						)}
						{!loading && items.length === 0 && (
							<tr>
								<td className="p-3" colSpan={4}>No employees</td>
							</tr>
						)}
						{items.map((e) => (
							<tr key={e.id} className="border-t">
								<td className="p-3">{e.name}</td>
								<td className="p-3">{e.status}</td>
								<td className="p-3">{e.updatedAt ?? '—'}</td>
								<td className="p-3 text-right space-x-2">
									<button className="px-2 py-1 rounded border" onClick={async () => { await startEmployee(e.id); refresh() }}>Start</button>
									<button className="px-2 py-1 rounded border" onClick={async () => { await stopEmployee(e.id); refresh() }}>Stop</button>
									<button className="px-2 py-1 rounded border">Logs</button>
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</div>
	)
}