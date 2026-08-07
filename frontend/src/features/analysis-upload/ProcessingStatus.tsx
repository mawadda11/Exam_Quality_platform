import { useCallback, useEffect, useRef, useState } from 'react'
import { getAnalysisProgress, retryAnalysis, runAnalysis } from '../../api/analyses'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { ProgressStepper, type ProgressStep } from '../../components/ui/ProgressStepper'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError, localizeServerMessage } from '../../i18n/localizeError'
import type {
  AnalysisResponse,
  ProcessingStage,
  ProgressResponse,
  QuestionPreparationMode,
} from '../../types/api'

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

const PROGRESS_REQUEST_TIMEOUT_MS = 15_000

const FACULTY_STAGES = [
  { id: 'files', label: 'Validating files', description: 'Checking the uploaded Exam and Course Specification files.' },
  { id: 'questions', label: 'Extracting questions', description: 'Reading questions, marks, and visible exam structure.' },
  { id: 'review', label: 'Reviewing extraction', description: 'Preparing the extracted questions for faculty review.' },
  { id: 'evidence', label: 'Preparing evidence', description: 'Preparing the confirmed extraction as analysis evidence.' },
  { id: 'knowledge', label: 'Retrieving evaluation knowledge', description: 'Retrieving the validated evaluation knowledge.' },
  { id: 'criteria', label: 'Applying evaluation criteria', description: 'Linking questions with evaluation criteria.' },
  { id: 'results', label: 'Generating results', description: 'Generating the findings and results.' },
] as const

const FACULTY_STAGE_INDEX: Partial<Record<ProcessingStage, number>> = {
  validating: 0,
  extracting_exam: 1,
  extracting_tp153: 1,
  review_ready: 2,
  building_evidence: 3,
  retrieving_knowledge: 4,
  applying_rules: 5,
  generating_report: 6,
  completed: 6,
}

function elapsedLabel(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

interface ProcessingStatusProps {
  analysisId: string
  initialState: ProcessingStage
  pollIntervalMs?: number
  onStateChange?: (state: ProcessingStage) => void
  onAnalysisStarted?: (analysis: AnalysisResponse) => void
  questionPreparationMode?: QuestionPreparationMode
}

export function ProcessingStatus({
  analysisId,
  initialState,
  pollIntervalMs = 1500,
  onStateChange,
  onAnalysisStarted,
  questionPreparationMode = 'assisted_pdf',
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
  const [requestTimedOut, setRequestTimedOut] = useState(false)
  const [failureDetailsLoaded, setFailureDetailsLoaded] = useState(false)
  const [elapsedClock, setElapsedClock] = useState<{
    stage: ProcessingStage
    seconds: number
  }>({ stage: initialState, seconds: 0 })

  useEffect(() => {
    onStateChangeRef.current = onStateChange
  }, [onStateChange])

  const hasStarted = state !== 'queued' || startRequested
  const isTerminal = TERMINAL_STAGES.includes(state)
  const needsFailureDetails = state === 'failed' && !failureDetailsLoaded
  const facultyStageIndex = FACULTY_STAGE_INDEX[state] ?? 0
  const facultyStage = FACULTY_STAGES[facultyStageIndex]
  const elapsedSeconds = elapsedClock.stage === state ? elapsedClock.seconds : 0

  useEffect(() => {
    if (!hasStarted || isTerminal) return undefined
    let seconds = 0
    const timer = globalThis.setInterval(() => {
      seconds += 1
      setElapsedClock({ stage: state, seconds })
    }, 1000)
    return () => globalThis.clearInterval(timer)
  }, [hasStarted, isTerminal, state])

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
      const controller = new AbortController()
      const requestTimeout = globalThis.setTimeout(
        () => controller.abort(),
        PROGRESS_REQUEST_TIMEOUT_MS,
      )
      try {
        const progress = await getAnalysisProgress(analysisId, controller.signal)
        if (cancelled) return
        setConnectivityDegraded(false)
        setRequestTimedOut(false)
        applyState(progress.state)
        setMessage(progress.message)
        setFailure({
          failed_stage: progress.failed_stage,
          error_code: progress.error_code,
          can_retry: progress.can_retry,
        })
        if (progress.state === 'failed') setFailureDetailsLoaded(true)
        shouldContinue = !TERMINAL_STAGES.includes(progress.state)
      } catch (pollError) {
        if (cancelled) return
        if (pollError instanceof DOMException && pollError.name === 'AbortError') {
          setRequestTimedOut(true)
        } else {
          setConnectivityDegraded(true)
        }
      } finally {
        globalThis.clearTimeout(requestTimeout)
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
    const currentIndex = FACULTY_STAGE_INDEX[currentState] ?? 0
    return FACULTY_STAGES.map((stage, index) => ({
      id: stage.id,
      label: t(stage.label),
      status: currentState === 'completed' || index < currentIndex
        ? 'complete'
        : index === currentIndex
          ? 'current'
          : 'upcoming',
    }))
  }

  async function handleStart(): Promise<void> {
    setIsStarting(true)
    setActionError(null)
    try {
      const response = await runAnalysis(analysisId, questionPreparationMode)
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
            {t('Current stage')}: <strong>{t(facultyStage.label)}</strong>
          </p>
          <p className="processing-stage-help">{t(facultyStage.description)}</p>
          {!isTerminal && (
            <p className="processing-elapsed">
              {t('Elapsed time')}: <bdi>{elapsedLabel(elapsedSeconds)}</bdi>
            </p>
          )}
        </>
      )}

      {connectivityDegraded && (
        <Alert variant="warning" title={t('Connection interrupted')}>
          {t('Progress could not be refreshed. Polling will retry automatically.')}
        </Alert>
      )}
      {requestTimedOut && (
        <Alert variant="warning" title={t('Progress check timed out')}>
          {t('The analysis is still running. Progress will be checked again automatically.')}
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
              {t('Stage needing attention')}:{' '}
              <strong>{t(FACULTY_STAGES[FACULTY_STAGE_INDEX[failure.failed_stage] ?? 0].label)}</strong>
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
