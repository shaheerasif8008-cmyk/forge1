import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

interface HealthStatus {
  status: string
  postgres?: boolean
  redis?: boolean
}

interface UserInfo {
  user_id: string
  tenant_id: string
}

export default function Dashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const token = sessionStorage.getItem('jwt_token')
    if (!token) {
      navigate('/login')
      return
    }

    const fetchData = async () => {
      try {
        // Fetch health status
        const healthResponse = await fetch(`${import.meta.env.VITE_API_URL}/health/ready`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (healthResponse.ok) {
          const healthData = await healthResponse.json()
          setHealth(healthData)
        }

        // Fetch user info
        const userResponse = await fetch(`${import.meta.env.VITE_API_URL}/auth/me`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (userResponse.ok) {
          const userData = await userResponse.json()
          setUserInfo(userData)
        }
      } catch (err) {
        setError('Failed to fetch dashboard data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [navigate])

  const handleLogout = () => {
    sessionStorage.setItem('jwt_token', '')
    navigate('/login')
  }

  const handleCreateEmployee = () => {
    // Placeholder - no backend call yet
    alert('Create Employee functionality coming soon!')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
      <div className="text-red-600 text-lg">{error}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <h1 className="text-3xl font-bold text-gray-900">Forge 1 Dashboard</h1>
            <div className="flex items-center space-x-4">
              <button
                onClick={handleCreateEmployee}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
              >
                Create Employee
              </button>
              <button
                onClick={handleLogout}
                className="text-gray-600 hover:text-gray-900 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Health Panel */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="health panel">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                  Backend Health Status
                </h3>
                {health ? (
                  <div className="space-y-3">
                    <div className="flex items-center">
                      <span className="text-sm font-medium text-gray-500 w-24">Status:</span>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        health.status === 'ready' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {health.status}
                      </span>
                    </div>
                    {health.postgres !== undefined && (
                      <div className="flex items-center">
                        <span className="text-sm font-medium text-gray-500 w-24">PostgreSQL:</span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          health.postgres ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {health.postgres ? 'Healthy' : 'Unhealthy'}
                        </span>
                      </div>
                    )}
                    {health.redis !== undefined && (
                      <div className="flex items-center">
                        <span className="text-sm font-medium text-gray-500 w-24">Redis:</span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          health.redis ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {health.redis ? 'Healthy' : 'Unhealthy'}
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-gray-500">Unable to fetch health status</p>
                )}
              </div>
            </div>

            {/* Who am I Panel */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                  Who am I
                </h3>
                {userInfo ? (
                  <div className="space-y-3">
                    <div className="flex items-center">
                      <span className="text-sm font-medium text-gray-500 w-24">User ID:</span>
                      <span className="text-sm text-gray-900 font-mono">{userInfo.user_id}</span>
                    </div>
                    <div className="flex items-center">
                      <span className="text-sm font-medium text-gray-500 w-24">Tenant ID:</span>
                      <span className="text-sm text-gray-900 font-mono">{userInfo.tenant_id}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-500">Unable to fetch user information</p>
                )}
              </div>
            </div>
          </div>

          {/* Additional Info */}
          <div className="mt-6 bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Quick Actions
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={handleCreateEmployee}
                  className="bg-indigo-600 text-white px-4 py-3 rounded-md hover:bg-indigo-700 transition-colors text-center"
                >
                  <div className="text-lg font-medium">Create Employee</div>
                  <div className="text-sm opacity-90">Build new AI employee</div>
                </button>
                <button className="bg-green-600 text-white px-4 py-3 rounded-md hover:bg-green-700 transition-colors text-center">
                  <div className="text-lg font-medium">Manage Employees</div>
                  <div className="text-sm opacity-90">View and configure</div>
                </button>
                <button className="bg-purple-600 text-white px-4 py-3 rounded-md hover:bg-purple-700 transition-colors text-center">
                  <div className="text-lg font-medium">Analytics</div>
                  <div className="text-sm opacity-90">Performance insights</div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
