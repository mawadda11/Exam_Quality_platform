import { Link } from 'react-router-dom'
import { PageHeader } from '../components/ui/PageHeader'
import { PageState } from '../components/ui/PageState'
import { AnalysisHistoryTable } from '../features/analysis-history/AnalysisHistoryTable'
import { AnalysisSummaryCards } from '../features/analysis-history/AnalysisSummaryCards'
import { calculateAnalysisMetrics } from '../features/analysis-history/analysisMetrics'
import { useAnalyses } from '../features/analysis-history/useAnalyses'

export function DashboardRoute() {
  const state = useAnalyses()
  const metrics =
    state.status === 'ready' ? calculateAnalysisMetrics(state.analyses) : null

  return (
    <div className="route-stack route-content-wide">
      <PageHeader
        eyebrow="Academic quality support"
        title="Dashboard"
        description="Create a new evidence-based exam analysis or return to an existing analysis."
        actions={
          <Link className="ui-button" to="/analyses/new">
            New Analysis
          </Link>
        }
      />

      {state.status === 'loading' && (
        <PageState state="loading" title="Loading dashboard" message="Retrieving your analyses…" />
      )}
      {state.status === 'error' && (
        <PageState state="error" title="Could not load dashboard" message={state.message} />
      )}
      {state.status === 'ready' && (
        <>
          <AnalysisSummaryCards analyses={state.analyses} />
          {metrics && metrics.recent.length > 0 ? (
            <section className="dashboard-recent">
              <div className="dashboard-section-heading">
                <h2>Recent analyses</h2>
                <Link to="/analyses">View all analyses</Link>
              </div>
              <AnalysisHistoryTable
                analyses={metrics.recent}
                caption="Recent analyses"
              />
            </section>
          ) : (
            <PageState
              state="empty"
              title="No analyses yet"
              message="Create an analysis to upload an exam and its populated TP-153."
              action={
                <Link className="ui-button" to="/analyses/new">
                  New Analysis
                </Link>
              }
            />
          )}
        </>
      )}
    </div>
  )
}
