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
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { PageState } from '../components/ui/PageState'
import { AnalysisWorkflowStepper } from '../features/analysis-upload/AnalysisWorkflowStepper'
import { AnalysisDocuments } from '../features/analysis-upload/AnalysisUploadFlow'
import { ProcessingStatus } from '../features/analysis-upload/ProcessingStatus'
import { ReviewStartSummary } from '../features/analysis-upload/ReviewStartSummary'
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

  async function retryAnalysisLoad(): Promise<void> {
    if (!analysisId || state.status !== 'error') return
    setState({ status: 'loading' })
    try {
      const analysis = await getAnalysis(analysisId)
      setState({ status: 'ready', analysis })
    } catch (error) {
      setState({
        status: 'error',
        analysisId,
        message:
          error instanceof ApiError ? error.detail : 'Could not load this analysis.',
      })
    }
  }

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
            <div className="route-actions">
              <Button variant="secondary" onClick={() => void retryAnalysisLoad()}>
                Retry analysis
              </Button>
              <Link className="ui-button ui-button--secondary" to="/analyses">
                Return to Analyses
              </Link>
            </div>
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

  if (analysis.state !== 'queued') {
    return <Navigate to={routeForAnalysis(analysis)} replace />
  }

  async function handleRefreshed(): Promise<void> {
    await refreshAnalysis()
  }

  return (
    <div className="route-stack route-content-form">
      <PageHeader
        title="Upload Documents"
        description="Upload the examination PDF and populated TP-153 required by this analysis."
      />
      <div className="analysis-workflow-stepper">
        <AnalysisWorkflowStepper currentStep="documents" />
      </div>
      <Card as="section" className="route-card">
        <AnalysisDocuments analysis={analysis} onRefreshed={handleRefreshed} />
      </Card>
      {analysis.ready_for_analysis && (
        <div className="workflow-route-actions workflow-route-actions--end">
          <Link className="ui-button" to={`/analyses/${analysis.id}/start`}>
            Continue to Review and Start
          </Link>
        </div>
      )}
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
    <div className="route-stack route-content-form">
      <PageHeader
        title="Review and Start"
        description="Review the persisted information and explicitly start the analysis when ready."
      />
      <div className="analysis-workflow-stepper">
        <AnalysisWorkflowStepper currentStep="review" />
      </div>
      <Card as="section" className="route-card">
        <ReviewStartSummary analysis={analysis} />
      </Card>
      <div className="workflow-route-actions">
        <Link className="ui-button ui-button--secondary" to={`/analyses/${analysis.id}/documents`}>
          Back to Upload Documents
        </Link>
        <ProcessingStatus
          analysisId={analysis.id}
          initialState={analysis.state}
          onAnalysisStarted={handleStarted}
        />
      </div>
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
      <div className="analysis-workflow-stepper">
        <AnalysisWorkflowStepper currentStep="complete" />
      </div>
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
