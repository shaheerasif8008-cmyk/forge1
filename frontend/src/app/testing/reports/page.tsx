"use client";

import { useState } from "react";

interface TestReport {
  id: string;
  testSuite: string;
  testRun: string;
  status: string;
  startTime: string;
  endTime: string | null;
  duration: number;
  concurrency: number;
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  avgResponseTime: number;
  p95ResponseTime: number;
  p99ResponseTime: number;
  throughput: number;
  errors: Array<{ type: string; count: number; percentage: number }>;
  reportType: string;
  fileSize: string;
  generatedAt: string;
  tags: string[];
}
import { AuthenticatedLayout } from "@/components/authenticated-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { 
  FileText, 
  Download, 
  Eye, 
  Search, 
  Filter, 
  Calendar, 
  Clock, 
  Users, 
  Zap,
  CheckCircle,
  XCircle,
  AlertTriangle,
  BarChart3,
  Trash2,
  Share2
} from "lucide-react";
import { toast } from "react-hot-toast";

// Mock data - replace with real API calls
const mockReports: TestReport[] = [
  {
    id: "report_001",
    testSuite: "Basic Load Test",
    testRun: "run_001",
    status: "completed",
    startTime: "2024-01-15T10:30:00Z",
    endTime: "2024-01-15T10:35:00Z",
    duration: 300,
    concurrency: 50,
    totalRequests: 15000,
    successfulRequests: 14750,
    failedRequests: 250,
    avgResponseTime: 245,
    p95ResponseTime: 420,
    p99ResponseTime: 680,
    throughput: 50,
    errors: [
      { type: "Connection Timeout", count: 180, percentage: 1.2 },
      { type: "Rate Limit Exceeded", count: 70, percentage: 0.47 },
    ],
    reportType: "html",
    fileSize: "2.4 MB",
    generatedAt: "2024-01-15T10:36:00Z",
    tags: ["load-test", "stable", "production"],
  },
  {
    id: "report_002",
    testSuite: "Stress Test - High Concurrency",
    testRun: "run_002",
    status: "completed",
    startTime: "2024-01-15T09:00:00Z",
    endTime: "2024-01-15T09:10:00Z",
    duration: 600,
    concurrency: 200,
    totalRequests: 25000,
    successfulRequests: 23500,
    failedRequests: 1500,
    avgResponseTime: 890,
    p95ResponseTime: 1560,
    p99ResponseTime: 2340,
    throughput: 41.7,
    errors: [
      { type: "Server Overload", count: 1200, percentage: 4.8 },
      { type: "Memory Limit Exceeded", count: 300, percentage: 1.2 },
    ],
    reportType: "pdf",
    fileSize: "3.8 MB",
    generatedAt: "2024-01-15T09:11:00Z",
    tags: ["stress-test", "high-concurrency", "breaking-point"],
  },
  {
    id: "report_003",
    testSuite: "Endurance Test",
    testRun: "run_003",
    status: "running",
    startTime: "2024-01-15T08:00:00Z",
    endTime: null,
    duration: 3600,
    concurrency: 25,
    totalRequests: 8000,
    successfulRequests: 7920,
    failedRequests: 80,
    avgResponseTime: 156,
    p95ResponseTime: 280,
    p99ResponseTime: 420,
    throughput: 2.2,
    errors: [
      { type: "Connection Timeout", count: 50, percentage: 0.63 },
      { type: "Validation Error", count: 30, percentage: 0.38 },
    ],
    reportType: "html",
    fileSize: "1.2 MB",
    generatedAt: "2024-01-15T08:01:00Z",
    tags: ["endurance", "stability", "long-running"],
  },
  {
    id: "report_004",
    testSuite: "Spike Test",
    testRun: "run_004",
    status: "failed",
    startTime: "2024-01-15T07:00:00Z",
    endTime: "2024-01-15T07:03:00Z",
    duration: 180,
    concurrency: 100,
    totalRequests: 12000,
    successfulRequests: 10500,
    failedRequests: 1500,
    avgResponseTime: 420,
    p95ResponseTime: 890,
    p99ResponseTime: 1560,
    throughput: 66.7,
    errors: [
      { type: "Server Overload", count: 1200, percentage: 10.0 },
      { type: "Connection Timeout", count: 300, percentage: 2.5 },
    ],
    reportType: "html",
    fileSize: "2.1 MB",
    generatedAt: "2024-01-15T07:04:00Z",
    tags: ["spike-test", "failed", "investigation-needed"],
  },
];

const reportTypes = ["all", "html", "pdf", "json"];
const statuses = ["all", "completed", "running", "failed"];
const testSuites = ["all", "Basic Load Test", "Stress Test - High Concurrency", "Endurance Test", "Spike Test"];

export default function ReportsPage() {
  const [reports, setReports] = useState(mockReports);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedSuite, setSelectedSuite] = useState("all");
  const [selectedReport, setSelectedReport] = useState<TestReport | null>(null);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);

  const filteredReports = reports.filter(report => {
    if (searchQuery && !report.testSuite.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (selectedType !== "all" && report.reportType !== selectedType) return false;
    if (selectedStatus !== "all" && report.status !== selectedStatus) return false;
    if (selectedSuite !== "all" && report.testSuite !== selectedSuite) return false;
    return true;
  });

  const handleDeleteReport = async (reportId: string) => {
    setReports(prev => prev.filter(r => r.id !== reportId));
    toast.success("Report deleted successfully!");
  };

  const handleDownloadReport = async (report: TestReport) => {
    // TODO: Implement actual download
    toast.success(`Downloading ${report.reportType.toUpperCase()} report...`);
  };

  const handleViewReport = (report: TestReport) => {
    setSelectedReport(report);
    setIsViewDialogOpen(true);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success">Completed</Badge>;
      case 'running':
        return <Badge variant="default" className="animate-pulse">Running</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getReportTypeIcon = (type: string) => {
    switch (type) {
      case 'html':
        return <FileText className="h-4 w-4 text-blue-600" />;
      case 'pdf':
        return <FileText className="h-4 w-4 text-red-600" />;
      case 'json':
        return <FileText className="h-4 w-4 text-green-600" />;
      default:
        return <FileText className="h-4 w-4 text-gray-600" />;
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
    return new Date(timestamp).toLocaleString();
  };

  const getSuccessRate = (report: TestReport) => {
    return ((report.successfulRequests / report.totalRequests) * 100).toFixed(1);
  };

  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Test Reports</h1>
            <p className="text-muted-foreground">
              View, download, and manage test execution reports
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline">
              <BarChart3 className="mr-2 h-4 w-4" />
              Generate Report
            </Button>
            <Button variant="outline">
              <Share2 className="mr-2 h-4 w-4" />
              Share Reports
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Search</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search reports..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">Report Type</label>
                <Select value={selectedType} onValueChange={setSelectedType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {reportTypes.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type === "all" ? "All Types" : type.toUpperCase()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Status</label>
                <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {statuses.map((status) => (
                      <SelectItem key={status} value={status}>
                        {status === "all" ? "All Statuses" : status.charAt(0).toUpperCase() + status.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Test Suite</label>
                <Select value={selectedSuite} onValueChange={setSelectedSuite}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {testSuites.map((suite) => (
                      <SelectItem key={suite} value={suite}>
                        {suite === "all" ? "All Suites" : suite}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Reports Table */}
        <Card>
          <CardHeader>
            <CardTitle>Test Reports</CardTitle>
            <CardDescription>
              {filteredReports.length} report{filteredReports.length !== 1 ? 's' : ''} found
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Test Suite</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Performance</TableHead>
                    <TableHead>Report</TableHead>
                    <TableHead>Generated</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredReports.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{report.testSuite}</div>
                          <div className="text-sm text-muted-foreground">
                            Run ID: {report.testRun}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>{getStatusBadge(report.status)}</TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Clock className="h-4 w-4 text-muted-foreground" />
                          <span>{formatDuration(report.duration)}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="text-sm">
                            <span className="font-medium">{getSuccessRate(report)}%</span> success
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {report.avgResponseTime}ms avg
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          {getReportTypeIcon(report.reportType)}
                          <div>
                            <div className="text-sm font-medium">{report.reportType.toUpperCase()}</div>
                            <div className="text-xs text-muted-foreground">{report.fileSize}</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {formatTimestamp(report.generatedAt)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewReport(report)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDownloadReport(report)}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteReport(report.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        {/* Report Details Dialog */}
        <Dialog open={isViewDialogOpen} onOpenChange={setIsViewDialogOpen}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Test Report Details</DialogTitle>
              <DialogDescription>
                Comprehensive details for {selectedReport?.testSuite}
              </DialogDescription>
            </DialogHeader>
            
            {selectedReport && (
              <div className="space-y-6">
                {/* Basic Information */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h3 className="font-semibold">Test Information</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Test Suite:</span>
                        <span className="font-medium">{selectedReport.testSuite}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Run ID:</span>
                        <span className="font-medium">{selectedReport.testRun}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Status:</span>
                        <span>{getStatusBadge(selectedReport.status)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Duration:</span>
                        <span className="font-medium">{formatDuration(selectedReport.duration)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold">Configuration</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Concurrency:</span>
                        <span className="font-medium">{selectedReport.concurrency}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Start Time:</span>
                        <span className="font-medium">{formatTimestamp(selectedReport.startTime)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">End Time:</span>
                        <span className="font-medium">
                          {selectedReport.endTime ? formatTimestamp(selectedReport.endTime) : "Running..."}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Generated:</span>
                        <span className="font-medium">{formatTimestamp(selectedReport.generatedAt)}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Performance Metrics */}
                <div className="space-y-4">
                  <h3 className="font-semibold">Performance Metrics</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {selectedReport.totalRequests.toLocaleString()}
                      </div>
                      <div className="text-sm text-muted-foreground">Total Requests</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {getSuccessRate(selectedReport)}%
                      </div>
                      <div className="text-sm text-muted-foreground">Success Rate</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-yellow-600">
                        {selectedReport.avgResponseTime}ms
                      </div>
                      <div className="text-sm text-muted-foreground">Avg Response</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {selectedReport.throughput}
                      </div>
                      <div className="text-sm text-muted-foreground">Throughput (req/s)</div>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Response Time Percentiles */}
                <div className="space-y-4">
                  <h3 className="font-semibold">Response Time Percentiles</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-xl font-bold text-blue-600">
                        {selectedReport.avgResponseTime}ms
                      </div>
                      <div className="text-sm text-muted-foreground">Average</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-xl font-bold text-yellow-600">
                        {selectedReport.p95ResponseTime}ms
                      </div>
                      <div className="text-sm text-muted-foreground">95th Percentile</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-xl font-bold text-red-600">
                        {selectedReport.p99ResponseTime}ms
                      </div>
                      <div className="text-sm text-muted-foreground">99th Percentile</div>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Error Analysis */}
                {selectedReport.errors.length > 0 && (
                  <>
                    <div className="space-y-4">
                      <h3 className="font-semibold">Error Analysis</h3>
                      <div className="space-y-2">
                        {selectedReport.errors.map((error: { type: string; count: number; percentage: number }, index: number) => (
                          <div key={index} className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-950 rounded-lg">
                            <div className="flex items-center space-x-2">
                              <XCircle className="h-4 w-4 text-red-600" />
                              <span className="font-medium">{error.type}</span>
                            </div>
                            <div className="text-right">
                              <div className="font-medium">{error.count}</div>
                              <div className="text-sm text-muted-foreground">{error.percentage}%</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <Separator />
                  </>
                )}

                {/* Tags */}
                <div className="space-y-4">
                  <h3 className="font-semibold">Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedReport.tags.map((tag: string, index: number) => (
                      <Badge key={index} variant="outline">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end space-x-2 pt-4">
                  <Button variant="outline" onClick={() => setIsViewDialogOpen(false)}>
                    Close
                  </Button>
                  <Button onClick={() => handleDownloadReport(selectedReport)}>
                    <Download className="mr-2 h-4 w-4" />
                    Download Report
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </AuthenticatedLayout>
  );
}