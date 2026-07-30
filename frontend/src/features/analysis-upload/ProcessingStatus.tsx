import { useCallback, useEffect, useRef, useState } from 'react'
import { getAnalysisProgress, retryAnalysis, runAnalysis } from '../../api/analyses'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { ProgressStepper, type ProgressStep } from '../../components/ui/ProgressStepper'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError, localizeServerMessage } from '../../i18n/localizeError'
import type { AnalysisResponse, ProcessingStage, ProgressResponse } from '../../types/api'

const TERMINAL_STAGES: ProcessingStage[] = ['review_ready', 'completed', 'failed']

const FAILURE_MESSAGE_KEYS: Record<string, string> = {
  FILE_VALIDATION_FAILED: 'The stored files could not be validated. Check that both PDFs are available, then retry.',
  EXAM_EXTRACTION_FAILED: 'The examination could not be extracted. Review the PDF and retry.',
  TP153_EXTRACTION_FAILED: 'The Course Specification could not be extracted. Review the PDF and retry.',
  EVIDENCE_BUILD_FAILED: 'The confirmed extraction could not be converted into analysis evidence. Retry the analysis.',
  KNOWLEDGE_RETRIEVAL_FAILED: 'The controlled knowledge base could not be prepared. Retry the analysis.',
  RULE_EVALUATION_FAILED: 'The academic checks could not be completed. Retry the analysis.',
  FINALIZATION_FAILED: 'The analysis could not be finalized. Retry the analysis.',
}

const ORDERED_PROCESSING_STAGES: ProcessingStage[] = [
  'validating',
  'extracting_exam',
  'extracting_tp153',
  'review_ready',
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

export function ProcessingStatus({
  analysisId,
  initialState,
  pollIntervalMs = 1500,
  onStateChange,
  onAnalysisStarted,
}: ProcessingStatusProps) {
  const { locale, t } = useI18n()
  const onStateChangeRef = useRef(onStateChange)
  const [state, setState] = useState<ProcessingStage>(initialState)
  const [message, setMessage] = useState<string | null>(null)
  const [failure, setFailure] = useState<Pick<ProgressResponse, 'failed_stage' | 'error_code' | 'can_retry'>>({
    failed_stage: null,
    error_code: null,
    can_retry: false,
  })
  const [isStarting, setIsStarting] = useState(false)
  const [isRetrying, setIsRetrying] = useState(false)
  const [startRequested, setStartRequested] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [retryNotice, setRetryNotice] = useState<string | null>(null)
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
        setFailure({
          failed_stage: progress.failed_stage,
          error_code: progress.error_code,
          can_retry: progress.can_retry,
        })
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
  }, [analysisId, applyState, hasStarted, isTerminal, needsFailureDetails, pollIntervalMs])

  function processingSteps(currentState: ProcessingStage): ProgressStep[] {
    const currentIndex = ORDERED_PROCESSING_STAGES.indexOf(currentState)
    return ORDERED_PROCESSING_STAGES.map((stage, index) => ({
      id: stage,
      label: t(stage),
      status: index < currentIndex ? 'complete' : index === currentIndex ? 'current' : 'upcoming',
    }))
  }

  async function handleStart(): Promise<void> {
    setIsStarting(true)
    setActionError(null)
    try {
      const response = await runAnalysis(analysisId)
      setStartRequested(true)
      applyState(response.state)
      onAnalysisStarted?.(response)
    } catch (error) {
      setStartRequested(false)
      setActionError(localizeInterfaceError(error, locale, t, 'Could not start analysis'))
    } finally {
      setIsStarting(false)
    }
  }

  async function handleRetry(): Promise<void> {
    setIsRetrying(true)
    setActionError(null)
    setRetryNotice(null)
    try {
      const response = await retryAnalysis(analysisId)
      setFailureDetailsLoaded(false)
      setFailure({ failed_stage: null, error_code: null, can_retry: false })
      setMessage(null)
      setRetryNotice(t('Retry accepted'))
      setStartRequested(true)
      applyState(response.state)
      onAnalysisStarted?.(response)
    } catch (error) {
      setActionError(localizeInterfaceError(error, locale, t, 'Analysis processing failed'))
    } finally {
      setIsRetrying(false)
    }
  }

  return (
    <div className="processing-status">
      {!hasStarted && (
        <Button
          onClick={() => void handleStart()}
          isLoading={isStarting}
          loadingLabel={t('Starting…')}
        >
          {t('Start Analysis')}
        </Button>
      )}

      {hasStarted && (
        <>
          {state !== 'failed' && state !== 'queued' && (
            <div className="processing-progress" tabIndex={0} aria-label={t('Processing stages')}>
              <ProgressStepper
                steps={processingSteps(state)}
                ariaLabel={t('Analysis processing progress')}
              />
            </div>
          )}
          <p className="processing-stage" role="status">
            {t('Current backend stage')}: <strong>{t(state)}</strong>
          </p>
        </>
      )}

      {connectivityDegraded && (
        <Alert variant="warning" title={t('Connection interrupted')}>
          {t('Progress could not be refreshed. Polling will retry automatically.')}
        </Alert>
      )}
      {state === 'failed' && (
        <Alert variant="error" title={t('Analysis processing failed')}>
          <p>
            {failure.error_code
              ? t(FAILURE_MESSAGE_KEYS[failure.error_code] ?? 'Analysis processing failed')
              : localizeServerMessage(message, locale, t, 'Analysis processing failed')}
          </p>
          {failure.failed_stage && (
            <p>
              {t('Current backend stage')}: <strong>{t(failure.failed_stage)}</strong>
            </p>
          )}
          {failure.error_code && <p><bdi>{failure.error_code}</bdi></p>}
          {failure.can_retry && (
            <Button
              variant="secondary"
              isLoading={isRetrying}
              loadingLabel={t('Retrying…')}
              onClick={() => void handleRetry()}
            >
              {t('Retry Analysis')}
            </Button>
          )}
        </Alert>
      )}
      {retryNotice && (
        <Alert variant="success" title={t('Retry accepted')}>
          {retryNotice}
        </Alert>
      )}
      {state === 'review_ready' && (
        <Alert variant="info" title={t('Extraction ready for review')}>
          {t('The extracted Exam and Course Specification evidence is ready. Continue to the dedicated review workspace to correct transcription, save a revision, and confirm it.')}
        </Alert>
      )}
      {actionError && (
        <Alert variant="error" title={t('Could not start analysis')}>
          {actionError}
        </Alert>
      )}
    </div>
  )
}
