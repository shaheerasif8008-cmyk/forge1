"use client";

import { useState, useEffect } from "react";
import { AuthenticatedLayout } from "@/components/authenticated-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { 
  LineChart, 
  Line, 
  AreaChart, 
  Area, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";
import { 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Users, 
  Zap, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Download,
  Calendar,
  Filter
} from "lucide-react";

// Mock data - replace with real API calls
const mockPerformanceData = {
  summary: {
    totalTests: 156,
    successfulTests: 142,
    failedTests: 14,
    avgResponseTime: 245,
    totalRequests: 1250000,
    successRate: 91.0,
  },
  trends: [
    { date: "2024-01-10", responseTime: 180, successRate: 95.2, requests: 85000 },
    { date: "2024-01-11", responseTime: 195, successRate: 94.8, requests: 92000 },
    { date: "2024-01-12", responseTime: 210, successRate: 93.5, requests: 88000 },
    { date: "2024-01-13", responseTime: 225, successRate: 92.1, requests: 95000 },
    { date: "2024-01-14", responseTime: 240, successRate: 91.3, requests: 102000 },
    { date: "2024-01-15", responseTime: 245, successRate: 91.0, requests: 98000 },
  ],
  hourlyData: [
    { hour: "00:00", responseTime: 220, requests: 4200, errors: 45 },
    { hour: "02:00", responseTime: 195, requests: 3800, errors: 32 },
    { hour: "04:00", responseTime: 180, requests: 3200, errors: 28 },
    { hour: "06:00", responseTime: 200, requests: 4100, errors: 38 },
    { hour: "08:00", responseTime: 280, requests: 6800, errors: 89 },
    { hour: "10:00", responseTime: 320, requests: 8200, errors: 156 },
    { hour: "12:00", responseTime: 350, requests: 9100, errors: 203 },
    { hour: "14:00", responseTime: 340, requests: 8800, errors: 178 },
    { hour: "16:00", responseTime: 310, requests: 7500, errors: 134 },
    { hour: "18:00", responseTime: 290, requests: 7200, errors: 112 },
    { hour: "20:00", responseTime: 260, requests: 5800, errors: 78 },
    { hour: "22:00", responseTime: 230, requests: 4800, errors: 56 },
  ],
  testSuitePerformance: [
    { name: "Basic Load Test", successRate: 98.5, avgResponseTime: 245, totalRuns: 45 },
    { name: "Stress Test", successRate: 94.2, avgResponseTime: 890, totalRuns: 23 },
    { name: "Endurance Test", successRate: 99.1, avgResponseTime: 156, totalRuns: 18 },
    { name: "Spike Test", successRate: 96.8, avgResponseTime: 420, totalRuns: 32 },
    { name: "API Integration", successRate: 87.3, avgResponseTime: 320, totalRuns: 28 },
  ],
  errorBreakdown: [
    { name: "Connection Timeout", value: 45, color: "#ef4444" },
    { name: "Rate Limit Exceeded", value: 32, color: "#f59e0b" },
    { name: "Server Error", value: 28, color: "#dc2626" },
    { name: "Validation Error", value: 22, color: "#7c3aed" },
    { name: "Authentication Failed", value: 18, color: "#059669" },
  ],
  concurrencyPerformance: [
    { concurrency: 10, responseTime: 120, successRate: 99.8 },
    { concurrency: 25, responseTime: 145, successRate: 99.5 },
    { concurrency: 50, responseTime: 180, successRate: 99.1 },
    { concurrency: 100, responseTime: 245, successRate: 98.2 },
    { concurrency: 200, responseTime: 420, successRate: 96.8 },
    { concurrency: 500, responseTime: 890, successRate: 92.1 },
    { concurrency: 1000, responseTime: 1560, successRate: 85.3 },
  ],
};

const timeRanges = [
  { value: "1h", label: "Last Hour" },
  { value: "6h", label: "Last 6 Hours" },
  { value: "24h", label: "Last 24 Hours" },
  { value: "7d", label: "Last 7 Days" },
  { value: "30d", label: "Last 30 Days" },
];

export default function PerformancePage() {
  const [selectedTimeRange, setSelectedTimeRange] = useState("7d");
  const [selectedMetric, setSelectedMetric] = useState("responseTime");

  const getMetricLabel = (metric: string) => {
    switch (metric) {
      case 'responseTime':
        return 'Response Time (ms)';
      case 'successRate':
        return 'Success Rate (%)';
      case 'requests':
        return 'Total Requests';
      default:
        return 'Response Time (ms)';
    }
  };

  const getMetricColor = (metric: string) => {
    switch (metric) {
      case 'responseTime':
        return '#3b82f6';
      case 'successRate':
        return '#10b981';
      case 'requests':
        return '#8b5cf6';
      default:
        return '#3b82f6';
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const getTrendIcon = (current: number, previous: number) => {
    if (current > previous) {
      return <TrendingUp className="h-4 w-4 text-red-600" />;
    } else if (current < previous) {
      return <TrendingDown className="h-4 w-4 text-green-600" />;
    }
    return null;
  };

  const getTrendDirection = (current: number, previous: number) => {
    if (current > previous) return "up";
    if (current < previous) return "down";
    return "stable";
  };

  const getStatusColor = (successRate: number) => {
    if (successRate >= 95) return "text-green-600";
    if (successRate >= 90) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Performance Dashboard</h1>
            <p className="text-muted-foreground">
              Comprehensive performance metrics and test result analysis
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Select value={selectedTimeRange} onValueChange={setSelectedTimeRange}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {timeRanges.map((range) => (
                  <SelectItem key={range.value} value={range.value}>
                    {range.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Export Report
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Tests</p>
                  <p className="text-2xl font-bold">{mockPerformanceData.summary.totalTests}</p>
                </div>
                <div className="h-12 w-12 rounded-lg bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                  <Zap className="h-6 w-6 text-blue-600" />
                </div>
              </div>
              <div className="mt-4 flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-muted-foreground">
                  {mockPerformanceData.summary.successfulTests} successful
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Success Rate</p>
                  <p className="text-2xl font-bold">{mockPerformanceData.summary.successRate}%</p>
                </div>
                <div className="h-12 w-12 rounded-lg bg-green-100 dark:bg-green-900 flex items-center justify-center">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                </div>
              </div>
              <div className="mt-4 flex items-center space-x-2">
                {getTrendIcon(
                  mockPerformanceData.trends[mockPerformanceData.trends.length - 1].successRate,
                  mockPerformanceData.trends[mockPerformanceData.trends.length - 2].successRate
                )}
                <span className="text-sm text-muted-foreground">
                  {getTrendDirection(
                    mockPerformanceData.trends[mockPerformanceData.trends.length - 1].successRate,
                    mockPerformanceData.trends[mockPerformanceData.trends.length - 2].successRate
                  ) === "down" ? "Improving" : "Declining"}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Avg Response Time</p>
                  <p className="text-2xl font-bold">{mockPerformanceData.summary.avgResponseTime}ms</p>
                </div>
                <div className="h-12 w-12 rounded-lg bg-yellow-100 dark:bg-yellow-900 flex items-center justify-center">
                  <Clock className="h-6 w-6 text-yellow-600" />
                </div>
              </div>
              <div className="mt-4 flex items-center space-x-2">
                {getTrendIcon(
                  mockPerformanceData.trends[mockPerformanceData.trends.length - 1].responseTime,
                  mockPerformanceData.trends[mockPerformanceData.trends.length - 2].responseTime
                )}
                <span className="text-sm text-muted-foreground">
                  {getTrendDirection(
                    mockPerformanceData.trends[mockPerformanceData.trends.length - 1].responseTime,
                    mockPerformanceData.trends[mockPerformanceData.trends.length - 2].responseTime
                  ) === "up" ? "Slower" : "Faster"}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Requests</p>
                  <p className="text-2xl font-bold">{formatNumber(mockPerformanceData.summary.totalRequests)}</p>
                </div>
                <div className="h-12 w-12 rounded-lg bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                  <Users className="h-6 w-6 text-purple-600" />
                </div>
              </div>
              <div className="mt-4 flex items-center space-x-2">
                <span className="text-sm text-muted-foreground">
                  {formatNumber(mockPerformanceData.summary.totalRequests / mockPerformanceData.summary.totalTests)} per test
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Response Time Trend */}
          <Card>
            <CardHeader>
              <CardTitle>Response Time Trend</CardTitle>
              <CardDescription>
                Average response time over the selected period
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={mockPerformanceData.trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="responseTime" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={{ fill: "#3b82f6", strokeWidth: 2, r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Success Rate Trend */}
          <Card>
            <CardHeader>
              <CardTitle>Success Rate Trend</CardTitle>
              <CardDescription>
                Test success rate over the selected period
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={mockPerformanceData.trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area 
                    type="monotone" 
                    dataKey="successRate" 
                    stroke="#10b981" 
                    fill="#10b981" 
                    fillOpacity={0.3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Hourly Performance */}
          <Card>
            <CardHeader>
              <CardTitle>Hourly Performance</CardTitle>
              <CardDescription>
                Response time and request volume by hour
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={mockPerformanceData.hourlyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Bar yAxisId="left" dataKey="responseTime" fill="#3b82f6" name="Response Time (ms)" />
                  <Bar yAxisId="right" dataKey="requests" fill="#8b5cf6" name="Requests" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Error Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Error Breakdown</CardTitle>
              <CardDescription>
                Distribution of error types
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={mockPerformanceData.errorBreakdown}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {mockPerformanceData.errorBreakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row 3 */}
        <div className="grid grid-cols-1 gap-6">
          {/* Concurrency Performance */}
          <Card>
            <CardHeader>
              <CardTitle>Concurrency Performance</CardTitle>
              <CardDescription>
                How system performance scales with concurrent users
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={mockPerformanceData.concurrencyPerformance}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="concurrency" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Line 
                    yAxisId="left"
                    type="monotone" 
                    dataKey="responseTime" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    name="Response Time (ms)"
                  />
                  <Line 
                    yAxisId="right"
                    type="monotone" 
                    dataKey="successRate" 
                    stroke="#10b981" 
                    strokeWidth={2}
                    name="Success Rate (%)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Test Suite Performance Table */}
        <Card>
          <CardHeader>
            <CardTitle>Test Suite Performance</CardTitle>
            <CardDescription>
              Performance metrics by test suite
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 font-medium">Test Suite</th>
                    <th className="text-center py-3 px-4 font-medium">Success Rate</th>
                    <th className="text-center py-3 px-4 font-medium">Avg Response Time</th>
                    <th className="text-center py-3 px-4 font-medium">Total Runs</th>
                    <th className="text-center py-3 px-4 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {mockPerformanceData.testSuitePerformance.map((suite, index) => (
                    <tr key={index} className="border-b hover:bg-accent/50">
                      <td className="py-3 px-4 font-medium">{suite.name}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={getStatusColor(suite.successRate)}>
                          {suite.successRate}%
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">{suite.avgResponseTime}ms</td>
                      <td className="py-3 px-4 text-center">{suite.totalRuns}</td>
                      <td className="py-3 px-4 text-center">
                        {suite.successRate >= 95 ? (
                          <Badge variant="success">Excellent</Badge>
                        ) : suite.successRate >= 90 ? (
                          <Badge variant="warning">Good</Badge>
                        ) : (
                          <Badge variant="destructive">Needs Attention</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </AuthenticatedLayout>
  );
}