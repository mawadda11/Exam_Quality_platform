import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { AnalysisResults } from '../features/analysis-results/AnalysisResults'
import { isResultsSectionId } from '../features/analysis-results/resultSections'
import { routeForAnalysis } from '../router/analysisRouting'
import { useAnalysisRoute } from './analysisRouteContext'

export function AnalysisResultsIndexRoute() {
  const { analysis } = useAnalysisRoute()
  if (analysis.state !== 'completed') {
    return <Navigate to={routeForAnalysis(analysis)} replace />
  }
  return <Navigate to={`/analyses/${analysis.id}/results/overview`} replace />
}

export function AnalysisResultsRoute() {
  const { analysis } = useAnalysisRoute()
  const { tab } = useParams()
  const navigate = useNavigate()

  if (analysis.state !== 'completed') {
    return <Navigate to={routeForAnalysis(analysis)} replace />
  }
  if (!isResultsSectionId(tab)) {
    return <Navigate to={`/analyses/${analysis.id}/results/overview`} replace />
  }

  return (
    <div className="route-stack route-content-wide">
      <AnalysisResults
        analysis={analysis}
        section={tab}
        onSectionChange={(section) =>
          navigate(`/analyses/${analysis.id}/results/${section}`)
        }
      />
    </div>
  )
}
