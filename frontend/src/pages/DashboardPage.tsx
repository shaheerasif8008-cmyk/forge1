import { useEffect, useState } from 'react'

type Health = { status: string; postgres: boolean; redis: boolean }
type User = { id: string; email: string; username?: string }

export default function DashboardPage() {
  const [health, setHealth] = useState<Health | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      window.location.href = '/login'
      return
    }

    // Fetch health status
    fetch(`${apiUrl}/api/v1/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setHealth(data))
      .catch(() => setHealth(null))

    // Fetch user info
    fetch(`${apiUrl}/api/v1/me`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [apiUrl])

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-semibold mb-6">Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Health Panel */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-medium mb-4">Backend Health</h2>
          {health ? (
            <ul className="space-y-2 text-sm">
              <li className="flex items-center">
                <span className="font-medium">Status:</span>
                <span className={`ml-2 px-2 py-1 rounded text-xs ${
                  health.status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {health.status}
                </span>
              </li>
              <li className="flex items-center">
                <span className="font-medium">Postgres:</span>
                <span className={`ml-2 px-2 py-1 rounded text-xs ${
                  health.postgres ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {String(health.postgres)}
                </span>
              </li>
              <li className="flex items-center">
                <span className="font-medium">Redis:</span>
                <span className={`ml-2 px-2 py-1 rounded text-xs ${
                  health.redis ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {String(health.redis)}
                </span>
              </li>
            </ul>
          ) : (
            <p className="text-gray-600 text-sm">Loading...</p>
          )}
        </div>

        {/* Who am I Panel */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-medium mb-4">Who am I</h2>
          {loading ? (
            <p className="text-gray-600 text-sm">Loading...</p>
          ) : user ? (
            <div className="space-y-2 text-sm">
              <p><span className="font-medium">ID:</span> {user.id}</p>
              <p><span className="font-medium">Email:</span> {user.email}</p>
              {user.username && <p><span className="font-medium">Username:</span> {user.username}</p>}
            </div>
          ) : (
            <p className="text-red-600 text-sm">Failed to load user info</p>
          )}
        </div>
      </div>

      {/* Create Employee Button */}
      <div className="mt-8 bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-medium mb-4">Actions</h2>
        <button
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
          onClick={() => alert('Create Employee functionality coming soon!')}
        >
          Create Employee
        </button>
      </div>
    </div>
  )
}


