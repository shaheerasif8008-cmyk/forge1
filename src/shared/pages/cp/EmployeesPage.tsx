import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import toast from 'react-hot-toast'

interface Employee {
	id: string
	name: string
	status: 'running' | 'stopped'
	role: string
}

export function EmployeesPage() {
	const [loading, setLoading] = useState(true)
	const [employees, setEmployees] = useState<Employee[]>([])

	async function load() {
		setLoading(true)
		try {
			const { data } = await api.get('/employees')
			setEmployees(data)
		} catch (e: any) {
			toast.error(e?.response?.data?.message || 'Failed to load employees')
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => { load() }, [])

	async function toggle(id: string, current: Employee['status']) {
		try {
			if (current === 'running') {
				await api.post(`/employees/${id}/stop`)
				toast.success('Stopped')
			} else {
				await api.post(`/employees/${id}/start`)
				toast.success('Started')
			}
			await load()
		} catch (e: any) {
			toast.error(e?.response?.data?.message || 'Action failed')
		}
	}

	return (
		<div className="space-y-4">
			<div className="flex items-center justify-between">
				<h1 className="text-xl font-semibold tracking-tight">Employees</h1>
				<button className="rounded-md border px-3 py-2 hover:bg-accent" onClick={load}>Refresh</button>
			</div>
			<div className="overflow-x-auto rounded-lg border">
				<table className="min-w-full text-sm">
					<thead className="bg-muted/50">
						<tr>
							<th className="text-left px-3 py-2">Name</th>
							<th className="text-left px-3 py-2">Role</th>
							<th className="text-left px-3 py-2">Status</th>
							<th className="text-right px-3 py-2">Actions</th>
						</tr>
					</thead>
					<tbody>
						{(loading ? Array.from({ length: 5 }) : employees).map((emp: any, idx: number) => (
							<tr key={emp?.id ?? idx} className="border-t">
								<td className="px-3 py-2">{loading ? <div className="h-4 w-40 bg-muted animate-pulse rounded" /> : emp.name}</td>
								<td className="px-3 py-2">{loading ? <div className="h-4 w-32 bg-muted animate-pulse rounded" /> : emp.role}</td>
								<td className="px-3 py-2">{loading ? <div className="h-4 w-24 bg-muted animate-pulse rounded" /> : (
									<span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs border ${emp.status === 'running' ? 'bg-green-500/10 text-green-600 border-green-600/30' : 'bg-amber-500/10 text-amber-600 border-amber-600/30'}`}>
										{emp.status}
									</span>
								)}</td>
								<td className="px-3 py-2 text-right">
									{loading ? (
										<div className="h-8 w-20 bg-muted animate-pulse rounded" />
									) : (
										<button className="rounded-md border px-3 py-1.5 hover:bg-accent" onClick={() => toggle(emp.id, emp.status)}>
											{emp.status === 'running' ? 'Stop' : 'Start'}
										</button>
									)}
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</div>
	)
}
