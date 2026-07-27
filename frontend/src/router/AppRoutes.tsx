import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
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

export function AppRoutes() {
  return (
    <Routes>
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
    </Routes>
  )
}
