import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { 
  Users, 
  DollarSign, 
  Activity, 
  Bot, 
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  Plus
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatCurrency } from '../../lib/utils';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';

// Mock data - replace with API calls
const mockStats = {
  totalEmployees: 12,
  activeEmployees: 8,
  monthlySpend: 2450.00,
  successRate: 94.5,
  trends: {
    employees: '+20%',
    spend: '+15%',
    successRate: '+2.3%'
  }
};

const mockChartData = [
  { name: 'Mon', tasks: 45, success: 42 },
  { name: 'Tue', tasks: 52, success: 49 },
  { name: 'Wed', tasks: 38, success: 36 },
  { name: 'Thu', tasks: 65, success: 61 },
  { name: 'Fri', tasks: 48, success: 45 },
  { name: 'Sat', tasks: 32, success: 30 },
  { name: 'Sun', tasks: 28, success: 26 },
];

const mockRecentActivity = [
  { id: 1, employee: 'Sales Assistant AI', action: 'Completed 15 outreach tasks', time: '2 hours ago', status: 'success' },
  { id: 2, employee: 'Customer Support AI', action: 'Resolved 8 tickets', time: '3 hours ago', status: 'success' },
  { id: 3, employee: 'Data Analyst AI', action: 'Generated weekly report', time: '5 hours ago', status: 'success' },
  { id: 4, employee: 'Marketing AI', action: 'Failed to process campaign', time: '6 hours ago', status: 'error' },
];

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate loading
    setTimeout(() => setLoading(false), 1000);
  }, []);

  const StatCard = ({ 
    title, 
    value, 
    trend, 
    icon: Icon, 
    color 
  }: { 
    title: string; 
    value: string | number; 
    trend: string; 
    icon: any; 
    color: string;
  }) => (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className={`h-4 w-4 ${color}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground flex items-center mt-1">
          {trend.startsWith('+') ? (
            <TrendingUp className="h-3 w-3 text-green-500 mr-1" />
          ) : (
            <TrendingDown className="h-3 w-3 text-red-500 mr-1" />
          )}
          <span className={trend.startsWith('+') ? 'text-green-500' : 'text-red-500'}>
            {trend}
          </span>
          <span className="ml-1">from last month</span>
        </p>
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-6"></div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor your AI employees and business metrics
          </p>
        </div>
        <Button asChild>
          <Link to="/builder">
            <Plus className="mr-2 h-4 w-4" />
            New Employee
          </Link>
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total AI Employees"
          value={mockStats.totalEmployees}
          trend={mockStats.trends.employees}
          icon={Bot}
          color="text-blue-500"
        />
        <StatCard
          title="Active Employees"
          value={mockStats.activeEmployees}
          trend="+2"
          icon={Users}
          color="text-green-500"
        />
        <StatCard
          title="Monthly Spend"
          value={formatCurrency(mockStats.monthlySpend)}
          trend={mockStats.trends.spend}
          icon={DollarSign}
          color="text-yellow-500"
        />
        <StatCard
          title="Success Rate"
          value={`${mockStats.successRate}%`}
          trend={mockStats.trends.successRate}
          icon={Activity}
          color="text-purple-500"
        />
      </div>

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Task Performance</CardTitle>
            <CardDescription>
              Daily task completion over the past week
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={mockChartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis 
                  dataKey="name" 
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                />
                <YAxis 
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px'
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="tasks"
                  stackId="1"
                  stroke="hsl(var(--primary))"
                  fill="hsl(var(--primary))"
                  fillOpacity={0.2}
                />
                <Area
                  type="monotone"
                  dataKey="success"
                  stackId="2"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Employee Activity</CardTitle>
            <CardDescription>
              Tasks processed per employee today
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={[
                { name: 'Sales AI', tasks: 45 },
                { name: 'Support AI', tasks: 38 },
                { name: 'Data AI', tasks: 28 },
                { name: 'Marketing AI', tasks: 32 },
                { name: 'Research AI', tasks: 25 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis 
                  dataKey="name" 
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis 
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px'
                  }}
                />
                <Bar 
                  dataKey="tasks" 
                  fill="hsl(var(--primary))"
                  radius={[8, 8, 0, 0]}
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
            Latest actions from your AI employees
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockRecentActivity.map((activity) => (
              <div key={activity.id} className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className={`h-2 w-2 rounded-full ${
                    activity.status === 'success' ? 'bg-green-500' : 'bg-red-500'
                  }`} />
                  <div>
                    <p className="text-sm font-medium">{activity.employee}</p>
                    <p className="text-sm text-muted-foreground">{activity.action}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-muted-foreground">{activity.time}</span>
                  <Button variant="ghost" size="sm" asChild>
                    <Link to={`/employees/${activity.id}`}>
                      <ArrowUpRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
