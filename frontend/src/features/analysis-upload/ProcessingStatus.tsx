import { useCallback, useEffect, useRef, useState } from 'react'
import { getAnalysisProgress, runAnalysis } from '../../api/analyses'
import { ApiError } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { ProgressStepper, type ProgressStep } from '../../components/ui/ProgressStepper'
import type { AnalysisResponse, ProcessingStage } from '../../types/api'

const TERMINAL_STAGES: ProcessingStage[] = ['completed', 'failed']
const ORDERED_PROCESSING_STAGES: ProcessingStage[] = [
  'validating',
  'extracting_exam',
  'extracting_tp153',
  'building_evidence',
  'retrieving_knowledge',
  'applying_rules',
  'generating_report',
  'completed',
]

interface ProcessingStatusProps {
  analysisId: string
  initialState: ProcessingStage
  pollIntervalMs?: number
  onStateChange?: (state: ProcessingStage) => void
  onAnalysisStarted?: (analysis: AnalysisResponse) => void
}

function processingSteps(currentState: ProcessingStage): ProgressStep[] {
  const currentIndex = ORDERED_PROCESSING_STAGES.indexOf(currentState)
  return ORDERED_PROCESSING_STAGES.map((stage, index) => ({
    id: stage,
    label: stage,
    status: index < currentIndex ? 'complete' : index === currentIndex ? 'current' : 'upcoming',
  }))
}

export function ProcessingStatus({
  analysisId,
  initialState,
  pollIntervalMs = 1500,
  onStateChange,
  onAnalysisStarted,
}: ProcessingStatusProps) {
  const onStateChangeRef = useRef(onStateChange)
  const [state, setState] = useState<ProcessingStage>(initialState)
  const [message, setMessage] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [startRequested, setStartRequested] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const [connectivityDegraded, setConnectivityDegraded] = useState(false)
  const [failureDetailsLoaded, setFailureDetailsLoaded] = useState(false)

  useEffect(() => {
    onStateChangeRef.current = onStateChange
  }, [onStateChange])

  const hasStarted = state !== 'queued' || startRequested
  const isTerminal = TERMINAL_STAGES.includes(state)
  const needsFailureDetails = state === 'failed' && !failureDetailsLoaded

  const applyState = useCallback((next: ProcessingStage): void => {
    setState(next)
    onStateChangeRef.current?.(next)
  }, [])

  useEffect(() => {
    if (!hasStarted || (isTerminal && !needsFailureDetails)) return undefined

    let cancelled = false
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    async function poll(): Promise<void> {
      let shouldContinue = true
      try {
        const progress = await getAnalysisProgress(analysisId)
        if (cancelled) return
        setConnectivityDegraded(false)
        applyState(progress.state)
        setMessage(progress.message)
        if (progress.state === 'failed') setFailureDetailsLoaded(true)
        shouldContinue = !TERMINAL_STAGES.includes(progress.state)
      } catch {
        if (cancelled) return
        setConnectivityDegraded(true)
      }

      if (!cancelled && shouldContinue) {
        timeoutId = setTimeout(() => void poll(), pollIntervalMs)
      }
    }

    void poll()
    return () => {
      cancelled = true
      if (timeoutId) clearTimeout(timeoutId)
    }
  }, [
    analysisId,
    applyState,
    hasStarted,
    isTerminal,
    needsFailureDetails,
    pollIntervalMs,
  ])

  async function handleStart(): Promise<void> {
    setIsStarting(true)
    setStartError(null)
    try {
      const response = await runAnalysis(analysisId)
      setStartRequested(true)
      applyState(response.state)
      onAnalysisStarted?.(response)
    } catch (error) {
      setStartRequested(false)
      setStartError(
        error instanceof ApiError ? error.detail : 'Could not start the analysis.',
      )
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <div className="processing-status">
      {!hasStarted && (
        <Button
          onClick={() => void handleStart()}
          isLoading={isStarting}
          loadingLabel="Starting…"
        >
          Start Analysis
        </Button>
      )}

      {hasStarted && (
        <>
          {state !== 'failed' && state !== 'queued' && (
            <div className="processing-progress" tabIndex={0} aria-label="Processing stages">
              <ProgressStepper
                steps={processingSteps(state)}
                ariaLabel="Analysis processing progress"
              />
            </div>
          )}
          <p className="processing-stage" role="status">
            Current backend stage: <strong>{state}</strong>
          </p>
        </>
      )}

      {connectivityDegraded && (
        <Alert variant="warning" title="Connection interrupted">
          Progress could not be refreshed. Polling will retry automatically.
        </Alert>
      )}
      {state === 'failed' && message && (
        <Alert variant="error" title="Analysis processing failed">
          {message}
        </Alert>
      )}
      {startError && (
        <Alert variant="error" title="Could not start analysis">
          {startError}
        </Alert>
      )}
    </div>
  )
}
