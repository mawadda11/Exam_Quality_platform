import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listAnalyses } from '../api/analyses'
import { ApiError } from '../api/client'
import { PageHeader } from '../components/ui/PageHeader'
import { PageState } from '../components/ui/PageState'
import { AnalysisHistoryList } from '../features/analysis-upload/AnalysisHistoryList'
import type { AnalysisResponse } from '../types/api'

type AnalysesState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; analyses: AnalysisResponse[] }

export function AnalysesRoute() {
  const [state, setState] = useState<AnalysesState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    listAnalyses()
      .then((analyses) => {
        if (!cancelled) setState({ status: 'ready', analyses })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message: error instanceof ApiError ? error.detail : 'Could not load analyses.',
        })
      })
    return () => {
      cancelled = true
    }
  }, [])

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
        <AnalysisHistoryList analyses={state.analyses} />
      )}
    </div>
  )
}
