import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { AuthLayout } from '../features/auth/AuthLayout'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { AnalysesRoute } from '../routes/AnalysesRoute'
import {
  AnalysisDocumentsRoute,
  AnalysisExtractionReviewRoute,
  AnalysisIndexRoute,
  AnalysisProgressRoute,
  AnalysisRouteLayout,
  AnalysisStartRoute,
} from '../routes/AnalysisWorkflowRoute'
import {
  AnalysisResultsIndexRoute,
  AnalysisResultsRoute,
} from '../routes/AnalysisResultsRoute'
import { DashboardRoute } from '../routes/DashboardRoute'
import { EvaluationScopeRoute } from '../routes/EvaluationScopeRoute'
import { NewAnalysisRoute } from '../routes/NewAnalysisRoute'
import { NotFoundRoute } from '../routes/NotFoundRoute'
import { ForgotPasswordRoute } from '../routes/auth/ForgotPasswordRoute'
import { LoginRoute } from '../routes/auth/LoginRoute'
import { RegisterRoute } from '../routes/auth/RegisterRoute'
import { ResetPasswordRoute } from '../routes/auth/ResetPasswordRoute'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/register" element={<RegisterRoute />} />
        <Route path="/forgot-password" element={<ForgotPasswordRoute />} />
        <Route path="/reset-password" element={<ResetPasswordRoute />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardRoute />} />
          <Route path="/analyses" element={<AnalysesRoute />} />
          <Route path="/analyses/new" element={<NewAnalysisRoute />} />
          <Route path="/evaluation-scope" element={<EvaluationScopeRoute />} />
          <Route path="/analyses/:analysisId" element={<AnalysisRouteLayout />}>
            <Route index element={<AnalysisIndexRoute />} />
            <Route path="documents" element={<AnalysisDocumentsRoute />} />
            <Route path="start" element={<AnalysisStartRoute />} />
            <Route path="progress" element={<AnalysisProgressRoute />} />
            <Route path="review" element={<AnalysisExtractionReviewRoute />} />
            <Route path="results" element={<AnalysisResultsIndexRoute />} />
            <Route path="results/:tab" element={<AnalysisResultsRoute />} />
            <Route path="*" element={<NotFoundRoute />} />
          </Route>
          <Route path="*" element={<NotFoundRoute />} />
        </Route>
      </Route>
    </Routes>
  )
}
