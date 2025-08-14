"use client"

import { useEffect, useState } from "react"
import { 
  Bot, 
  Activity, 
  DollarSign, 
  TrendingUp,
  Clock,
  CheckCircle,
  AlertTriangle,
  Plus
} from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuthStore } from "@/stores/auth"

// Mock data - would come from API
const mockStats = {
  totalEmployees: 12,
  activeEmployees: 8,
  totalRequests: 15420,
  successRate: 97.8,
  monthlyRevenue: 2840,
  growthRate: 12.5
}

const mockActivityData = [
  { date: "2024-01", requests: 1200, success: 1150 },
  { date: "2024-02", requests: 1800, success: 1750 },
  { date: "2024-03", requests: 2400, success: 2300 },
  { date: "2024-04", requests: 3200, success: 3100 },
  { date: "2024-05", requests: 2800, success: 2750 },
  { date: "2024-06", requests: 3600, success: 3520 }
]

const mockEmployeePerformance = [
  { name: "Customer Support Bot", requests: 4500, success: 98.2 },
  { name: "Content Generator", requests: 3200, success: 96.8 },
  { name: "Data Analyzer", requests: 2800, success: 99.1 },
  { name: "Email Assistant", requests: 2100, success: 95.4 },
  { name: "Chat Moderator", requests: 1900, success: 97.6 }
]

const mockRecentActivity = [
  {
    id: "1",
    type: "employee_created",
    description: "New employee Sales Assistant created",
    timestamp: "2 minutes ago",
    icon: Bot,
    color: "text-green-600"
  },
  {
    id: "2", 
    type: "request_completed",
    description: "1,000 requests processed successfully",
    timestamp: "15 minutes ago",
    icon: CheckCircle,
    color: "text-blue-600"
  },
  {
    id: "3",
    type: "alert",
    description: "High response time detected on Customer Support Bot",
    timestamp: "1 hour ago",
    icon: AlertTriangle,
    color: "text-yellow-600"
  },
  {
    id: "4",
    type: "employee_updated",
    description: "Content Generator configuration updated",
    timestamp: "3 hours ago",
    icon: Bot,
    color: "text-purple-600"
  }
]

export default function DashboardPage() {
  const { user } = useAuthStore()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            Welcome back, {user?.firstName}!
          </h1>
          <p className="text-muted-foreground mt-1">
            Here&apos;s what&apos;s happening with your AI workforce today.
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Create Employee
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Employees</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.totalEmployees}</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">{mockStats.activeEmployees} active</span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.totalRequests.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="inline h-3 w-3 mr-1" />
              +12% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.successRate}%</div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="inline h-3 w-3 mr-1" />
              +0.2% from last week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${mockStats.monthlyRevenue.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="inline h-3 w-3 mr-1" />
              +{mockStats.growthRate}% from last month
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Section */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Activity Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Request Activity</CardTitle>
            <CardDescription>
              Monthly request volume and success rate
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={mockActivityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="requests" 
                  stroke="hsl(var(--primary))" 
                  strokeWidth={2}
                  name="Total Requests"
                />
                <Line 
                  type="monotone" 
                  dataKey="success" 
                  stroke="hsl(var(--chart-2))" 
                  strokeWidth={2}
                  name="Successful Requests"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Employee Performance */}
        <Card>
          <CardHeader>
            <CardTitle>Employee Performance</CardTitle>
            <CardDescription>
              Request volume by AI employee
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={mockEmployeePerformance} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={120} />
                <Tooltip />
                <Bar 
                  dataKey="requests" 
                  fill="hsl(var(--primary))" 
                  name="Requests"
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>
            Latest updates from your AI workforce
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockRecentActivity.map((activity) => (
              <div key={activity.id} className="flex items-center space-x-4">
                <div className={`p-2 rounded-full bg-muted ${activity.color}`}>
                  <activity.icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{activity.description}</p>
                  <p className="text-xs text-muted-foreground flex items-center">
                    <Clock className="mr-1 h-3 w-3" />
                    {activity.timestamp}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}