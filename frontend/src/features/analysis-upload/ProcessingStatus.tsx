import { useEffect, useState } from 'react'
import { getAnalysisProgress, runAnalysis } from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { ProcessingStage } from '../../types/api'

const TERMINAL_STAGES: ProcessingStage[] = ['completed', 'failed']

function formatStage(stage: ProcessingStage): string {
  const spaced = stage.replaceAll('_', ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

interface ProcessingStatusProps {
  analysisId: string
  initialState: ProcessingStage
  pollIntervalMs?: number
  onStateChange?: (state: ProcessingStage) => void
}

export function ProcessingStatus({
  analysisId,
  initialState,
  pollIntervalMs = 1500,
  onStateChange,
}: ProcessingStatusProps) {
  const [state, setState] = useState<ProcessingStage>(initialState)
  const [message, setMessage] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  const hasStarted = state !== 'queued'
  const isTerminal = TERMINAL_STAGES.includes(state)

  function applyState(next: ProcessingStage): void {
    setState(next)
    onStateChange?.(next)
  }

  useEffect(() => {
    if (!hasStarted || isTerminal) return undefined

    let cancelled = false
    const interval = setInterval(() => {
      getAnalysisProgress(analysisId)
        .then((progress) => {
          if (cancelled) return
          applyState(progress.state)
          setMessage(progress.message)
        })
        .catch(() => {
          // Transient polling failure - retry on the next tick.
        })
    }, pollIntervalMs)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysisId, hasStarted, isTerminal, pollIntervalMs])

  async function handleStart(): Promise<void> {
    setIsStarting(true)
    setStartError(null)
    try {
      const response = await runAnalysis(analysisId)
      applyState(response.state)
    } catch (err) {
      setStartError(err instanceof ApiError ? err.detail : 'Could not start the analysis.')
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <div className="processing-status">
      {!hasStarted && (
        <button type="button" onClick={() => void handleStart()} disabled={isStarting}>
          {isStarting ? 'Starting…' : 'Start analysis'}
        </button>
      )}
      {hasStarted && (
        <p className="processing-stage" role="status">
          Current stage: <strong>{formatStage(state)}</strong>
        </p>
      )}
      {state === 'failed' && message && (
        <p className="field-error" role="alert">
          {message}
        </p>
      )}
      {startError && (
        <p className="field-error" role="alert">
          {startError}
        </p>
      )}
    </div>
  )
}
