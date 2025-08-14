"use client";

import { useState } from "react";
import { AuthenticatedLayout } from "@/components/authenticated-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Play, Pause, RotateCcw, Settings, BarChart3, Clock, Users, Zap, Database } from "lucide-react";
import { toast } from "react-hot-toast";

// Mock data - replace with real API calls
const testSuites = [
  {
    id: "suite_001",
    name: "Basic Load Test",
    description: "Standard load testing with moderate concurrency",
    status: "idle", // idle, running, completed, failed
    lastRun: "2024-01-15T10:30:00Z",
    duration: 300, // seconds
    concurrency: 50,
    datasetSize: "medium",
    successRate: 98.5,
    avgResponseTime: 245,
    totalRequests: 15000,
    category: "load",
    tags: ["basic", "load", "stable"],
  },
  {
    id: "suite_002",
    name: "Stress Test - High Concurrency",
    description: "High concurrency stress testing to find breaking points",
    status: "completed",
    lastRun: "2024-01-14T15:45:00Z",
    duration: 600,
    concurrency: 200,
    datasetSize: "large",
    successRate: 94.2,
    avgResponseTime: 890,
    totalRequests: 25000,
    category: "stress",
    tags: ["stress", "high-concurrency", "breaking-point"],
  },
  {
    id: "suite_003",
    name: "Endurance Test",
    description: "Long-running test to check system stability over time",
    status: "running",
    lastRun: "2024-01-15T08:00:00Z",
    duration: 3600,
    concurrency: 25,
    datasetSize: "small",
    successRate: 99.1,
    avgResponseTime: 156,
    totalRequests: 8000,
    category: "endurance",
    tags: ["endurance", "stability", "long-running"],
  },
  {
    id: "suite_004",
    name: "Spike Test",
    description: "Sudden traffic spikes to test system resilience",
    status: "idle",
    lastRun: "2024-01-13T12:20:00Z",
    duration: 180,
    concurrency: 100,
    datasetSize: "medium",
    successRate: 96.8,
    avgResponseTime: 420,
    totalRequests: 12000,
    category: "spike",
    tags: ["spike", "resilience", "traffic"],
  },
  {
    id: "suite_005",
    name: "API Integration Test",
    description: "Test all API endpoints and integrations",
    status: "failed",
    lastRun: "2024-01-15T09:15:00Z",
    duration: 120,
    concurrency: 10,
    datasetSize: "small",
    successRate: 87.3,
    avgResponseTime: 320,
    totalRequests: 3000,
    category: "integration",
    tags: ["api", "integration", "endpoints"],
  },
];

const categories = [
  { id: "all", name: "All Tests", count: testSuites.length },
  { id: "load", name: "Load Tests", count: testSuites.filter(s => s.category === "load").length },
  { id: "stress", name: "Stress Tests", count: testSuites.filter(s => s.category === "stress").length },
  { id: "endurance", name: "Endurance Tests", count: testSuites.filter(s => s.category === "endurance").length },
  { id: "spike", name: "Spike Tests", count: testSuites.filter(s => s.category === "spike").length },
  { id: "integration", name: "Integration Tests", count: testSuites.filter(s => s.category === "integration").length },
];

export default function TestSuitesPage() {
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [runningTests, setRunningTests] = useState<string[]>([]);

  const filteredSuites = selectedCategory === "all" 
    ? testSuites 
    : testSuites.filter(suite => suite.category === selectedCategory);

  const handleStartTest = async (suiteId: string) => {
    setRunningTests(prev => [...prev, suiteId]);
    // TODO: Implement API call to start test
    await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API call
    setRunningTests(prev => prev.filter(id => id !== suiteId));
    toast.success("Test started successfully!");
  };

  const handleStopTest = async (suiteId: string) => {
    // TODO: Implement API call to stop test
    toast.success("Test stopped successfully!");
  };

  const handleResetTest = async (suiteId: string) => {
    // TODO: Implement API call to reset test
    toast.success("Test reset successfully!");
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return <Badge variant="success" className="animate-pulse">Running</Badge>;
      case 'completed':
        return <Badge variant="default">Completed</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      case 'idle':
      default:
        return <Badge variant="secondary">Idle</Badge>;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'load':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'stress':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'endurance':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'spike':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'integration':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  const formatLastRun = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    return `${diffDays} days ago`;
  };

  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-semibold">Test Suites</h1>
          <p className="text-muted-foreground">
            Select and run predefined test configurations for your AI employees
          </p>
        </div>

        {/* Category Filter */}
        <div className="flex flex-wrap gap-2">
          {categories.map((category) => (
            <Button
              key={category.id}
              variant={selectedCategory === category.id ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(category.id)}
            >
              {category.name}
              <Badge variant="secondary" className="ml-2">
                {category.count}
              </Badge>
            </Button>
          ))}
        </div>

        {/* Test Suites Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSuites.map((suite) => (
            <Card key={suite.id} className="relative">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">{suite.name}</CardTitle>
                    <CardDescription className="text-sm">
                      {suite.description}
                    </CardDescription>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getStatusBadge(suite.status)}
                    <Badge 
                      variant="outline" 
                      className={`${getCategoryColor(suite.category)} border-0`}
                    >
                      {suite.category}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4">
                {/* Test Configuration */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-muted-foreground">
                      <Clock className="h-4 w-4" />
                      <span>Duration</span>
                    </div>
                    <div className="font-medium">{formatDuration(suite.duration)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-muted-foreground">
                      <Users className="h-4 w-4" />
                      <span>Concurrency</span>
                    </div>
                    <div className="font-medium">{suite.concurrency}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-muted-foreground">
                      <Database className="h-4 w-4" />
                      <span>Dataset</span>
                    </div>
                    <div className="font-medium capitalize">{suite.datasetSize}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-muted-foreground">
                      <Zap className="h-4 w-4" />
                      <span>Last Run</span>
                    </div>
                    <div className="font-medium">{formatLastRun(suite.lastRun)}</div>
                  </div>
                </div>

                {/* Last Run Results */}
                {suite.status !== "idle" && (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Success Rate</span>
                        <span className="font-medium">{suite.successRate}%</span>
                      </div>
                      <Progress value={suite.successRate} className="h-2" />
                      
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <div className="text-muted-foreground">Avg Response</div>
                          <div className="font-medium">{suite.avgResponseTime}ms</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Total Requests</div>
                          <div className="font-medium">{suite.totalRequests.toLocaleString()}</div>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {/* Action Buttons */}
                <div className="flex items-center space-x-2 pt-4">
                  {suite.status === "running" ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStopTest(suite.id)}
                      className="flex-1"
                    >
                      <Pause className="mr-2 h-4 w-4" />
                      Stop
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => handleStartTest(suite.id)}
                      disabled={runningTests.includes(suite.id)}
                      className="flex-1"
                    >
                      {runningTests.includes(suite.id) ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                          Starting...
                        </>
                      ) : (
                        <>
                          <Play className="mr-2 h-4 w-4" />
                          Start
                        </>
                      )}
                    </Button>
                  )}
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleResetTest(suite.id)}
                  >
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {/* TODO: Navigate to test details */}}
                  >
                    <BarChart3 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common testing operations and configurations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              <Button variant="outline">
                <Settings className="mr-2 h-4 w-4" />
                Create Custom Test
              </Button>
              <Button variant="outline">
                <BarChart3 className="mr-2 h-4 w-4" />
                View Test History
              </Button>
              <Button variant="outline">
                <Zap className="mr-2 h-4 w-4" />
                Run All Tests
              </Button>
              <Button variant="outline">
                <Database className="mr-2 h-4 w-4" />
                Manage Test Data
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AuthenticatedLayout>
  );
}