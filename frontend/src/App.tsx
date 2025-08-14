import { Navigate, Route, Routes } from "react-router-dom";
import { SessionProvider, useSession } from "./components/SessionManager";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ToastProvider } from "./components/Toast";
import { LoadingSpinner } from "./components/LoadingSpinner";
import { lazy, Suspense } from "react";
import LoginPage from "./pages/LoginPage";
const RegisterPage = lazy(()=> import('./pages/RegisterPage'));
const VerifyPage = lazy(()=> import('./pages/VerifyPage'));
const ForgotPage = lazy(()=> import('./pages/ForgotPage'));
const ResetPage = lazy(()=> import('./pages/ResetPage'));
const MfaSetupPage = lazy(()=> import('./pages/MfaSetupPage'));
const MfaVerifyPage = lazy(()=> import('./pages/MfaVerifyPage'));
const AdminUsersPage = lazy(()=> import('./pages/AdminUsersPage'));
// Legacy DashboardPage kept for reference; not used after premium dashboard
// const DashboardPage = lazy(()=> import('./pages/DashboardPage'));
const MetricsPage = lazy(()=> import('./pages/MetricsPage'));
const AdminMonitoringPage = lazy(()=> import('./pages/AdminMonitoringPage'));
const AdminAICommsPage = lazy(()=> import('./pages/AdminAICommsPage'));
const AdminFeatureFlagsPage = lazy(()=> import('./pages/AdminFeatureFlagsPage'));
const AdminErrorsPage = lazy(()=> import('./pages/AdminErrorsPage'));
const MarketplacePage = lazy(()=> import('./pages/MarketplacePage'));
const PipelinesPage = lazy(()=> import('./pages/PipelinesPage'));
const EmployeeChatPage = lazy(()=> import('./pages/EmployeeChatPage'));
const EmployeeWizardPage = lazy(()=> import('./pages/EmployeeWizardPage'));
const EmployeeDetailPage = lazy(()=> import('./pages/EmployeeDetailPage'));
const DocsSite = lazy(()=> import('./pages/DocsSite'));
const ClientDashboardPage = lazy(()=> import('./pages/ClientDashboardPage'));
const OnboardingWizardPage = lazy(()=> import('./pages/OnboardingWizardPage'));
// AssistantPanel is used embedded by consumers, not directly routed here
// const AssistantPanel = lazy(()=> import('./pages/AssistantPanel'));
import { ThemeProvider } from "./pages/ThemeProvider";
const TestingLabDashboard = lazy(()=> import('./pages/TestingLabDashboard'));
const TestingLabSuitesPage = lazy(()=> import('./pages/TestingLabSuitesPage'));
const TestingLabRunDetailPage = lazy(()=> import('./pages/TestingLabRunDetailPage'));
const TestingLabReportsPage = lazy(()=> import('./pages/TestingLabReportsPage'));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useSession();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  const { isAuthenticated } = useSession();

  return (
    <Routes>
      <Route 
        path="/testing"
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <TestingLabDashboard />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route 
        path="/testing/suites"
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <TestingLabSuitesPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route 
        path="/testing/runs/:id"
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <TestingLabRunDetailPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route 
        path="/testing/reports"
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <TestingLabReportsPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route 
        path="/login" 
        element={
          isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />
        } 
      />
      <Route path="/register" element={<Suspense fallback={<div className="p-6">Loading…</div>}><RegisterPage /></Suspense>} />
      <Route path="/verify" element={<Suspense fallback={<div className="p-6">Loading…</div>}><VerifyPage /></Suspense>} />
      <Route path="/forgot" element={<Suspense fallback={<div className="p-6">Loading…</div>}><ForgotPage /></Suspense>} />
      <Route path="/reset" element={<Suspense fallback={<div className="p-6">Loading…</div>}><ResetPage /></Suspense>} />
      <Route 
        path="/dashboard" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <ClientDashboardPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/onboarding" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <OnboardingWizardPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/beta/metrics" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <MetricsPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin/monitoring" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <AdminMonitoringPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin/ai-comms" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <AdminAICommsPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin/feature-flags" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <AdminFeatureFlagsPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin/errors" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <AdminErrorsPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/marketplace" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <MarketplacePage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/pipelines" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <PipelinesPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin/users" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <AdminUsersPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/mfa/setup" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <MfaSetupPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/mfa/verify" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <MfaVerifyPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/employees/:employeeId/chat" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <EmployeeChatPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/employees/new" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <EmployeeWizardPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/employees/:employeeId" 
        element={
          <ProtectedRoute>
            <Suspense fallback={<div className="p-6">Loading…</div>}>
              <EmployeeDetailPage />
            </Suspense>
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/docs" 
        element={
          <Suspense fallback={<div className="p-6">Loading…</div>}>
            <DocsSite />
          </Suspense>
        } 
      />
      <Route 
        path="*" 
        element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />} 
      />
    </Routes>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <SessionProvider>
          <ThemeProvider>
            <div className="min-h-screen bg-gray-50 text-gray-900">
              <Suspense fallback={<div className="p-6">Loading…</div>}>
                <AppRoutes />
              </Suspense>
            </div>
          </ThemeProvider>
        </SessionProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;
