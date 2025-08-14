// User and Authentication Types
export interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  role: 'admin' | 'user'
  createdAt: string
  updatedAt: string
  subscription?: Subscription
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  firstName: string
  lastName: string
}

export interface AuthResponse {
  user: User
  token: string
  refreshToken: string
}

// AI Employee Types
export interface AIEmployee {
  id: string
  name: string
  description: string
  type: 'chatbot' | 'analyzer' | 'generator' | 'classifier'
  status: 'active' | 'inactive' | 'training' | 'error'
  config: EmployeeConfig
  performance: EmployeePerformance
  createdAt: string
  updatedAt: string
  userId: string
}

export interface EmployeeConfig {
  model: string
  temperature: number
  maxTokens: number
  systemPrompt: string
  tools: string[]
  knowledgeBase?: string[]
}

export interface EmployeePerformance {
  totalRequests: number
  successRate: number
  avgResponseTime: number
  lastActive: string
  dailyStats: DailyStats[]
}

export interface DailyStats {
  date: string
  requests: number
  successes: number
  failures: number
  avgResponseTime: number
}

// Subscription and Billing Types
export interface Subscription {
  id: string
  plan: 'free' | 'pro' | 'enterprise'
  status: 'active' | 'canceled' | 'past_due'
  currentPeriodStart: string
  currentPeriodEnd: string
  cancelAtPeriodEnd: boolean
  usage: Usage
}

export interface Usage {
  requests: number
  storage: number
  employees: number
  limits: {
    requests: number
    storage: number
    employees: number
  }
}

// Testing App Types
export interface TestSuite {
  id: string
  name: string
  description: string
  type: 'load' | 'stress' | 'functional' | 'performance'
  config: TestConfig
  lastRun?: string
  status: 'ready' | 'running' | 'completed' | 'failed'
}

export interface TestConfig {
  duration: number
  concurrency: number
  requestsPerSecond: number
  datasetSize: number
  endpoints: string[]
  scenarios: TestScenario[]
}

export interface TestScenario {
  id: string
  name: string
  weight: number
  requests: TestRequest[]
}

export interface TestRequest {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  endpoint: string
  headers?: Record<string, string>
  body?: any
  validation?: ResponseValidation
}

export interface ResponseValidation {
  statusCode: number
  responseTime: number
  bodyContains?: string[]
}

export interface TestRun {
  id: string
  suiteId: string
  startTime: string
  endTime?: string
  status: 'running' | 'completed' | 'failed' | 'canceled'
  results: TestResults
  logs: TestLog[]
}

export interface TestResults {
  totalRequests: number
  successfulRequests: number
  failedRequests: number
  avgResponseTime: number
  minResponseTime: number
  maxResponseTime: number
  throughput: number
  errorRate: number
  metrics: PerformanceMetrics
}

export interface PerformanceMetrics {
  cpu: MetricDataPoint[]
  memory: MetricDataPoint[]
  network: MetricDataPoint[]
  latency: MetricDataPoint[]
}

export interface MetricDataPoint {
  timestamp: string
  value: number
}

export interface TestLog {
  timestamp: string
  level: 'info' | 'warning' | 'error'
  message: string
  data?: any
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
  hasMore: boolean
}

// Dashboard Types
export interface DashboardStats {
  totalEmployees: number
  activeEmployees: number
  totalRequests: number
  successRate: number
  monthlyUsage: Usage
  recentActivity: ActivityItem[]
}

export interface ActivityItem {
  id: string
  type: 'employee_created' | 'employee_updated' | 'request_made' | 'test_run'
  description: string
  timestamp: string
  metadata?: any
}