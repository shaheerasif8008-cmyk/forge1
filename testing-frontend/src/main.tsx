import React from 'react'
import ReactDOM from 'react-dom/client'
import { AppProviders } from './providers/AppProviders'
import './index.css'
import { createBrowserRouter, RouterProvider, Route, createRoutesFromElements } from 'react-router-dom'
import TestingSuitesPage from './pages/TestingSuites'
import TestingRunsPage from './pages/TestingRuns'
import TestingRunDetailPage from './pages/TestingRunDetail'
import TestingReportsPage from './pages/TestingReports'
import { AdminJwtBanner } from './components/layout/Banner'

function Redirect({ to }: { to: string }) {
  React.useEffect(() => { window.location.replace(to) }, [to])
  return null
}

const router = createBrowserRouter(
  createRoutesFromElements(
    <Route path="/testing">
      <Route index element={<Redirect to="/testing/suites" />} />
      <Route path="suites" element={<TestingSuitesPage />} />
      <Route path="runs" element={<TestingRunsPage />} />
      <Route path="runs/:id" element={<TestingRunDetailPage />} />
      <Route path="reports" element={<TestingReportsPage />} />
    </Route>
  )
)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProviders>
      <AdminJwtBanner />
      <RouterProvider router={router} />
    </AppProviders>
  </React.StrictMode>
)


