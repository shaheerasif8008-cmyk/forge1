import { useEffect, useState } from 'react'

type Health = { status: string; postgres: boolean; redis: boolean }

export default function DashboardPage() {
  const [health, setHealth] = useState<Health | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      window.location.href = '/login'
      return
    }
    fetch('/api/v1/health')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setHealth(data))
      .catch(() => setHealth(null))
  }, [])

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-3xl font-semibold mb-4">Dashboard</h1>
      <div className="bg-white rounded shadow p-4">
        <h2 className="text-xl font-medium">Backend Health</h2>
        {health ? (
          <ul className="list-disc list-inside mt-2 text-sm">
            <li>Status: {health.status}</li>
            <li>Postgres: {String(health.postgres)}</li>
            <li>Redis: {String(health.redis)}</li>
          </ul>
        ) : (
          <p className="text-gray-600 text-sm mt-2">Loading...</p>
        )}
      </div>
    </div>
  )
}


