"use client";

import { useState, useEffect } from "react";
import { AuthenticatedLayout } from "@/components/authenticated-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Filter, 
  Search, 
  Download, 
  Eye, 
  EyeOff,
  AlertCircle,
  CheckCircle,
  Info,
  Clock,
  Zap,
  Users,
  Activity
} from "lucide-react";
import { toast } from "react-hot-toast";

// Mock data - replace with real SSE/WebSocket data
const mockTestRuns = [
  {
    id: "run_001",
    suiteName: "Basic Load Test",
    status: "running",
    startTime: "2024-01-15T10:30:00Z",
    duration: 180,
    maxDuration: 300,
    concurrency: 50,
    currentConcurrency: 45,
    totalRequests: 12500,
    successfulRequests: 12250,
    failedRequests: 250,
    avgResponseTime: 245,
    currentResponseTime: 280,
    errors: [
      { timestamp: "2024-01-15T10:32:15Z", message: "Connection timeout", count: 15 },
      { timestamp: "2024-01-15T10:31:45Z", message: "Rate limit exceeded", count: 8 },
    ],
    logs: [
      { timestamp: "2024-01-15T10:32:20Z", level: "info", message: "Test iteration 125 completed" },
      { timestamp: "2024-01-15T10:32:18Z", level: "info", message: "Test iteration 124 completed" },
      { timestamp: "2024-01-15T10:32:15Z", level: "error", message: "Connection timeout for request 123" },
      { timestamp: "2024-01-15T10:32:12Z", level: "info", message: "Test iteration 122 completed" },
      { timestamp: "2024-01-15T10:32:10Z", level: "warning", message: "Response time increased to 320ms" },
    ],
  },
  {
    id: "run_002",
    suiteName: "Stress Test - High Concurrency",
    status: "completed",
    startTime: "2024-01-15T09:00:00Z",
    duration: 600,
    maxDuration: 600,
    concurrency: 200,
    currentConcurrency: 0,
    totalRequests: 25000,
    successfulRequests: 23500,
    failedRequests: 1500,
    avgResponseTime: 890,
    currentResponseTime: 0,
    errors: [
      { timestamp: "2024-01-15T09:58:30Z", message: "Server overload", count: 1200 },
      { timestamp: "2024-01-15T09:55:15Z", message: "Memory limit exceeded", count: 300 },
    ],
    logs: [
      { timestamp: "2024-01-15T09:59:45Z", level: "info", message: "Test completed successfully" },
      { timestamp: "2024-01-15T09:58:30Z", level: "error", message: "Server overload detected" },
      { timestamp: "2024-01-15T09:55:15Z", level: "error", message: "Memory limit exceeded" },
    ],
  },
];

const logLevels = ["all", "info", "warning", "error"];
const logLevelColors = {
  info: "text-blue-600",
  warning: "text-yellow-600",
  error: "text-red-600",
};

export default function LiveMonitorPage() {
  const [testRuns, setTestRuns] = useState(mockTestRuns);
  const [selectedTestRun, setSelectedTestRun] = useState<string | null>(null);
  const [logFilter, setLogFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showErrors, setShowErrors] = useState(true);
  const [showWarnings, setShowWarnings] = useState(true);
  const [showInfo, setShowInfo] = useState(true);

  // Simulate real-time updates
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      setTestRuns(prev => prev.map(run => {
        if (run.status === "running") {
          return {
            ...run,
            duration: run.duration + 1,
            totalRequests: run.totalRequests + Math.floor(Math.random() * 10) + 1,
            successfulRequests: run.successfulRequests + Math.floor(Math.random() * 8) + 1,
            failedRequests: run.failedRequests + Math.floor(Math.random() * 3),
            currentResponseTime: run.avgResponseTime + Math.floor(Math.random() * 100) - 50,
            logs: [
              {
                timestamp: new Date().toISOString(),
                level: "info",
                message: `Test iteration ${run.totalRequests + 1} completed`,
              },
              ...run.logs.slice(0, 49), // Keep last 50 logs
            ],
          };
        }
        return run;
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  const handleStopTest = async (runId: string) => {
    setTestRuns(prev => prev.map(run => 
      run.id === runId ? { ...run, status: "stopped" } : run
    ));
    toast.success("Test stopped successfully!");
  };

  const handleResetTest = async (runId: string) => {
    setTestRuns(prev => prev.map(run => 
      run.id === runId ? { ...run, status: "idle", duration: 0, totalRequests: 0, successfulRequests: 0, failedRequests: 0 } : run
    ));
    toast.success("Test reset successfully!");
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return <Badge variant="success" className="animate-pulse">Running</Badge>;
      case 'completed':
        return <Badge variant="default">Completed</Badge>;
      case 'stopped':
        return <Badge variant="warning">Stopped</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="secondary">Idle</Badge>;
    }
  };

  const getLogLevelIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4 text-yellow-600" />;
      case 'info':
        return <Info className="h-4 w-4 text-blue-600" />;
      default:
        return <Info className="h-4 w-4 text-gray-600" />;
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

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const filteredLogs = selectedTestRun ? 
    testRuns.find(run => run.id === selectedTestRun)?.logs.filter(log => {
      if (logFilter !== "all" && log.level !== logFilter) return false;
      if (!showErrors && log.level === "error") return false;
      if (!showWarnings && log.level === "warning") return false;
      if (!showInfo && log.level === "info") return false;
      if (searchQuery && !log.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    }) || [] : [];

  const selectedRun = testRuns.find(run => run.id === selectedTestRun);

  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Live Test Monitor</h1>
            <p className="text-muted-foreground">
              Monitor real-time test execution and performance metrics
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-2">
              <Switch
                id="autoRefresh"
                checked={autoRefresh}
                onCheckedChange={setAutoRefresh}
              />
              <Label htmlFor="autoRefresh">Auto-refresh</Label>
            </div>
            <Button variant="outline" size="sm">
              <Download className="mr-2 h-4 w-4" />
              Export Logs
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Test Runs Overview */}
          <div className="lg:col-span-1 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="h-5 w-5" />
                  <span>Active Tests</span>
                </CardTitle>
                <CardDescription>
                  Currently running test suites
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {testRuns.filter(run => run.status === "running").map((run) => (
                  <div key={run.id} className="p-3 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-sm">{run.suiteName}</h4>
                      {getStatusBadge(run.status)}
                    </div>
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Duration:</span>
                        <span>{formatDuration(run.duration)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Requests:</span>
                        <span>{run.totalRequests.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Success Rate:</span>
                        <span>{((run.successfulRequests / run.totalRequests) * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 mt-3">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleStopTest(run.id)}
                        className="flex-1"
                      >
                        <Pause className="h-3 w-3 mr-1" />
                        Stop
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedTestRun(run.id)}
                      >
                        <Eye className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}
                
                {testRuns.filter(run => run.status === "running").length === 0 && (
                  <div className="text-center text-muted-foreground py-8">
                    <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No active tests</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Test History */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Tests</CardTitle>
                <CardDescription>
                  Recently completed test runs
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {testRuns.filter(run => run.status !== "running").slice(0, 5).map((run) => (
                  <div 
                    key={run.id} 
                    className={`p-3 border rounded-lg cursor-pointer hover:bg-accent transition-colors ${
                      selectedTestRun === run.id ? 'border-primary bg-accent' : ''
                    }`}
                    onClick={() => setSelectedTestRun(run.id)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-sm">{run.suiteName}</h4>
                      {getStatusBadge(run.status)}
                    </div>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <div>Duration: {formatDuration(run.duration)}</div>
                      <div>Requests: {run.totalRequests.toLocaleString()}</div>
                      <div>Success: {((run.successfulRequests / run.totalRequests) * 100).toFixed(1)}%</div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Test Details and Logs */}
          <div className="lg:col-span-2 space-y-4">
            {selectedRun ? (
              <>
                {/* Test Details */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle>{selectedRun.suiteName}</CardTitle>
                        <CardDescription>
                          Test run details and performance metrics
                        </CardDescription>
                      </div>
                      <div className="flex items-center space-x-2">
                        {getStatusBadge(selectedRun.status)}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleResetTest(selectedRun.id)}
                        >
                          <RotateCcw className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="text-center">
                        <div className="text-2xl font-bold">{formatDuration(selectedRun.duration)}</div>
                        <div className="text-sm text-muted-foreground">Duration</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold">{selectedRun.totalRequests.toLocaleString()}</div>
                        <div className="text-sm text-muted-foreground">Total Requests</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold">{selectedRun.currentResponseTime}ms</div>
                        <div className="text-sm text-muted-foreground">Response Time</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold">{((selectedRun.successfulRequests / selectedRun.totalRequests) * 100).toFixed(1)}%</div>
                        <div className="text-sm text-muted-foreground">Success Rate</div>
                      </div>
                    </div>

                    {/* Progress Bars */}
                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between text-sm mb-2">
                          <span>Test Progress</span>
                          <span>{Math.round((selectedRun.duration / selectedRun.maxDuration) * 100)}%</span>
                        </div>
                        <Progress value={(selectedRun.duration / selectedRun.maxDuration) * 100} className="h-2" />
                      </div>
                      
                      <div>
                        <div className="flex justify-between text-sm mb-2">
                          <span>Concurrency</span>
                          <span>{selectedRun.currentConcurrency}/{selectedRun.concurrency}</span>
                        </div>
                        <Progress value={(selectedRun.currentConcurrency / selectedRun.concurrency) * 100} className="h-2" />
                      </div>
                    </div>

                    {/* Errors Summary */}
                    {selectedRun.errors.length > 0 && (
                      <div className="mt-6">
                        <h4 className="font-medium mb-3">Recent Errors</h4>
                        <div className="space-y-2">
                          {selectedRun.errors.slice(0, 3).map((error, index) => (
                            <div key={index} className="flex items-center justify-between p-2 bg-red-50 dark:bg-red-950 rounded text-sm">
                              <span className="text-red-700 dark:text-red-300">{error.message}</span>
                              <Badge variant="destructive">{error.count}</Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Live Logs */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>Live Logs</CardTitle>
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center space-x-2">
                          <Switch
                            id="showErrors"
                            checked={showErrors}
                            onCheckedChange={setShowErrors}
                          />
                          <Label htmlFor="showErrors" className="text-sm">Errors</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Switch
                            id="showWarnings"
                            checked={showWarnings}
                            onCheckedChange={setShowWarnings}
                          />
                          <Label htmlFor="showWarnings" className="text-sm">Warnings</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Switch
                            id="showInfo"
                            checked={showInfo}
                            onCheckedChange={setShowInfo}
                          />
                          <Label htmlFor="showInfo" className="text-sm">Info</Label>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Log Filters */}
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center space-x-2">
                          <Label htmlFor="logLevel" className="text-sm">Log Level:</Label>
                          <Select value={logFilter} onValueChange={setLogFilter}>
                            <SelectTrigger className="w-32">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {logLevels.map((level) => (
                                <SelectItem key={level} value={level}>
                                  {level.charAt(0).toUpperCase() + level.slice(1)}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Search className="h-4 w-4 text-muted-foreground" />
                          <Input
                            placeholder="Search logs..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-64"
                          />
                        </div>
                      </div>

                      {/* Logs Display */}
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm">
                        {filteredLogs.length > 0 ? (
                          <div className="space-y-1">
                            {filteredLogs.map((log, index) => (
                              <div key={index} className="flex items-start space-x-3">
                                <span className="text-muted-foreground text-xs min-w-[60px]">
                                  {formatTimestamp(log.timestamp)}
                                </span>
                                <span className="min-w-[20px]">
                                  {getLogLevelIcon(log.level)}
                                </span>
                                <span className={`${logLevelColors[log.level as keyof typeof logLevelColors] || 'text-gray-600'}`}>
                                  {log.message}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center text-muted-foreground py-8">
                            <Filter className="h-8 w-8 mx-auto mb-2 opacity-50" />
                            <p>No logs match the current filters</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card className="h-96">
                <CardContent className="flex items-center justify-center h-full">
                  <div className="text-center text-muted-foreground">
                    <Eye className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Select a test run to view details and logs</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </AuthenticatedLayout>
  );
}