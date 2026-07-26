import { useCallback, useEffect, useState } from 'react'
import {
  Link,
  Navigate,
  Outlet,
  useNavigate,
  useParams,
} from 'react-router-dom'
import { getAnalysis } from '../api/analyses'
import { ApiError } from '../api/client'
import { Card } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { PageState } from '../components/ui/PageState'
import { AnalysisDocuments } from '../features/analysis-upload/AnalysisUploadFlow'
import { ProcessingStatus } from '../features/analysis-upload/ProcessingStatus'
import { routeForAnalysis } from '../router/analysisRouting'
import type { AnalysisResponse, ProcessingStage } from '../types/api'
import { type AnalysisRouteContext, useAnalysisRoute } from './analysisRouteContext'

type AnalysisLoadState =
  | { status: 'loading' }
  | { status: 'error'; analysisId: string; message: string }
  | { status: 'ready'; analysis: AnalysisResponse }

export function AnalysisRouteLayout() {
  const { analysisId } = useParams()
  const [state, setState] = useState<AnalysisLoadState>({ status: 'loading' })

  useEffect(() => {
    if (!analysisId) return undefined

    let cancelled = false
    getAnalysis(analysisId)
      .then((analysis) => {
        if (!cancelled) setState({ status: 'ready', analysis })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          analysisId,
          message: error instanceof ApiError ? error.detail : 'Could not load this analysis.',
        })
      })
    return () => {
      cancelled = true
    }
  }, [analysisId])

  const refreshAnalysis = useCallback(async (): Promise<AnalysisResponse> => {
    if (!analysisId) throw new Error('No analysis identifier was provided.')
    const analysis = await getAnalysis(analysisId)
    setState({ status: 'ready', analysis })
    return analysis
  }, [analysisId])

  const replaceAnalysis = useCallback((analysis: AnalysisResponse): void => {
    setState({ status: 'ready', analysis })
  }, [])

  const updateAnalysisState = useCallback((nextState: ProcessingStage): void => {
    setState((current) =>
      current.status === 'ready'
        ? { status: 'ready', analysis: { ...current.analysis, state: nextState } }
        : current,
    )
  }, [])

  if (!analysisId) {
    return (
      <div className="route-content-compact">
        <PageState
          state="error"
          title="Could not open analysis"
          message="No analysis identifier was provided."
        />
      </div>
    )
  }

  const routeIsLoading =
    state.status === 'loading' ||
    (state.status === 'ready' && state.analysis.id !== analysisId) ||
    (state.status === 'error' && state.analysisId !== analysisId)

  if (routeIsLoading) {
    return (
      <div className="route-content-compact">
        <PageState
          state="loading"
          title="Loading analysis"
          message="Retrieving the selected analysis…"
        />
      </div>
    )
  }

  if (state.status === 'error') {
    return (
      <div className="route-content-compact">
        <PageState
          state="error"
          title="Could not open analysis"
          message={state.message}
          action={
            <Link className="ui-button ui-button--secondary" to="/analyses">
              Return to Analyses
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <Outlet
      context={{
        analysis: state.analysis,
        refreshAnalysis,
        replaceAnalysis,
        updateAnalysisState,
      } satisfies AnalysisRouteContext}
    />
  )
}

export function AnalysisIndexRoute() {
  const { analysis } = useAnalysisRoute()
  return <Navigate to={routeForAnalysis(analysis)} replace />
}

export function AnalysisDocumentsRoute() {
  const { analysis, refreshAnalysis } = useAnalysisRoute()
  const navigate = useNavigate()

  if (analysis.state !== 'queued' || analysis.ready_for_analysis) {
    return <Navigate to={routeForAnalysis(analysis)} replace />
  }

  async function handleRefreshed(): Promise<void> {
    const refreshed = await refreshAnalysis()
    if (refreshed.ready_for_analysis) {
      navigate(`/analyses/${refreshed.id}/start`)
    }
  }

  return (
    <div className="route-stack route-content-form">
      <PageHeader
        title="Upload Documents"
        description="Upload the examination PDF and populated TP-153 required by this analysis."
      />
      <Card as="section" className="route-card">
        <AnalysisDocuments analysis={analysis} onRefreshed={handleRefreshed} />
      </Card>
    </div>
  )
}

export function AnalysisStartRoute() {
  const { analysis, replaceAnalysis } = useAnalysisRoute()
  const navigate = useNavigate()

  if (analysis.state !== 'queued' || !analysis.ready_for_analysis) {
    return <Navigate to={routeForAnalysis(analysis)} replace />
  }

  function handleStarted(started: AnalysisResponse): void {
    replaceAnalysis(started)
    navigate(routeForAnalysis(started), { replace: true })
  }

  return (
    <div className="route-stack route-content-compact">
      <PageHeader
        title="Start Analysis"
        description="Both required documents are uploaded. Start the existing analysis workflow."
      />
      <Card as="section" className="route-card">
        <h2>
          <bdi>{analysis.course.code}</bdi> — {analysis.exam_type}
        </h2>
        <p>Term: {analysis.term}</p>
        <ProcessingStatus
          analysisId={analysis.id}
          initialState={analysis.state}
          onAnalysisStarted={handleStarted}
        />
      </Card>
    </div>
  )
}

export function AnalysisProgressRoute() {
  const { analysis, updateAnalysisState } = useAnalysisRoute()
  const navigate = useNavigate()

  if (analysis.state === 'queued' || analysis.state === 'completed') {
    return <Navigate to={routeForAnalysis(analysis)} replace />
  }

  function handleStateChange(state: ProcessingStage): void {
    updateAnalysisState(state)
    if (state === 'completed') {
      navigate(`/analyses/${analysis.id}/results/overview`, { replace: true })
    }
  }

  return (
    <div className="route-stack route-content-compact">
      <PageHeader
        title="Analysis Progress"
        description="Processing continues through the existing backend workflow."
      />
      <Card as="section" className="route-card">
        <h2>
          <bdi>{analysis.course.code}</bdi> — {analysis.exam_type}
        </h2>
        <ProcessingStatus
          analysisId={analysis.id}
          initialState={analysis.state}
          onStateChange={handleStateChange}
        />
      </Card>
    </div>
  )
}
