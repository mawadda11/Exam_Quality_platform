import { Link } from 'react-router-dom'
import { PageHeader } from '../components/ui/PageHeader'
import { PageState } from '../components/ui/PageState'
import { AnalysisHistoryTable } from '../features/analysis-history/AnalysisHistoryTable'
import { useAnalyses } from '../features/analysis-history/useAnalyses'

export function AnalysesRoute() {
  const state = useAnalyses()

  return (
    <div className="route-stack route-content-wide">
      <PageHeader
        title="Analyses"
        description="Open an existing analysis or begin a new one."
        actions={
          <Link className="ui-button" to="/analyses/new">
            New Analysis
          </Link>
        }
      />
      {state.status === 'loading' && (
        <PageState state="loading" title="Loading analyses" message="Retrieving your analyses…" />
      )}
      {state.status === 'error' && (
        <PageState state="error" title="Could not load analyses" message={state.message} />
      )}
      {state.status === 'ready' && state.analyses.length === 0 && (
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
      {state.status === 'ready' && state.analyses.length > 0 && (
        <AnalysisHistoryTable analyses={state.analyses} caption="All analyses" />
      )}
    </div>
  )
}
