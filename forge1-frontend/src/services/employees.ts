import { api } from '../lib/api'

export type Employee = {
	id: string
	name: string
	status: 'idle' | 'running' | 'stopped' | 'error'
	updatedAt?: string
}

export async function listEmployees(): Promise<Employee[]> {
	const res = await api.get('/api/v1/employees')
	return res.data
}

export async function startEmployee(id: string): Promise<void> {
	await api.post(`/api/v1/employees/${id}/start`)
}

export async function stopEmployee(id: string): Promise<void> {
	await api.post(`/api/v1/employees/${id}/stop`)
}