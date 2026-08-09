import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { AnalysisResponse, ProgressResponse } from '../../types/api'
import { ProcessingStatus } from './ProcessingStatus'

vi.mock('../../api/analyses')

beforeEach(() => {
  vi.clearAllMocks()
})

function analysisResponse(state: AnalysisResponse['state']): AnalysisResponse {
  return {
    id: 'analysis-1',
    course: {
      id: 'course-1',
      code: 'CPIT-450',
      name: 'SE',
      department: null,
      program: null,
    },
    exam_type: 'Midterm',
    term: '2026 Spring',
    state,
    owner_user_id: 'user-1',
    predecessor_analysis_id: null,
    uploaded_files: [],
    exam_uploaded: true,
    tp153_uploaded: true,
    ready_for_analysis: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function progressResponse(
  state: ProgressResponse['state'],
  message: string | null = null,
): ProgressResponse {
  return {
    analysis_id: 'analysis-1',
    state,
    message,
    failed_stage: state === 'failed' ? 'extracting_exam' : null,
    error_code: state === 'failed' ? 'EXAM_EXTRACTION_FAILED' : null,
    can_retry: state === 'failed',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

describe('ProcessingStatus', () => {
  it('requires an explicit action before starting the analysis', () => {
    render(<ProcessingStatus analysisId="analysis-1" initialState="queued" />)

    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument()
    expect(analysesApi.runAnalysis).not.toHaveBeenCalled()
    expect(analysesApi.getAnalysisProgress).not.toHaveBeenCalled()
  })

  it('starts after the explicit action and shows a faculty-facing stage label', async () => {
    vi.mocked(analysesApi.runAnalysis).mockResolvedValue(analysisResponse('validating'))
    vi.mocked(analysesApi.getAnalysisProgress).mockImplementation(
      () => new Promise(() => undefined),
    )
    render(<ProcessingStatus analysisId="analysis-1" initialState="queued" />)

    fireEvent.click(screen.getByRole('button', { name: /start analysis/i }))

    expect(await screen.findByText('Validating files', { selector: 'strong' })).toBeInTheDocument()
    expect(screen.queryByText('validating')).not.toBeInTheDocument()
    const progress = screen.getByRole('list', { name: /analysis processing progress/i })
    expect(within(progress).getAllByRole('listitem')).toHaveLength(7)
    expect(within(progress).getByText('Reviewing extraction')).toBeInTheDocument()
    expect(screen.getByText(/elapsed time/i)).toBeInTheDocument()
    expect(analysesApi.runAnalysis).toHaveBeenCalledWith('analysis-1', 'assisted_pdf')
  })

  it('keeps the seven stages readable at 320px and 200% zoom without horizontal scrolling', () => {
    const originalWidth = window.innerWidth
    const originalFontSize = document.documentElement.style.fontSize
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 320 })
    document.documentElement.style.fontSize = '200%'
    vi.mocked(analysesApi.getAnalysisProgress).mockImplementation(
      () => new Promise(() => undefined),
    )

    try {
      render(<ProcessingStatus analysisId="analysis-1" initialState="validating" />)

      const progress = screen.getByRole('list', { name: /analysis processing progress/i })
      expect(within(progress).getAllByRole('listitem')).toHaveLength(7)
      expect(within(progress).getByText('Retrieving evaluation knowledge')).toBeInTheDocument()
      expect(progress.parentElement).toHaveClass('processing-progress')
      expect(progress.parentElement).not.toHaveStyle({ overflowX: 'auto' })
    } finally {
      Object.defineProperty(window, 'innerWidth', {
        configurable: true,
        value: originalWidth,
      })
      document.documentElement.style.fontSize = originalFontSize
    }
  })


  it('passes the selected structured preparation mode to the run API', async () => {
    vi.mocked(analysesApi.runAnalysis).mockResolvedValue(analysisResponse('validating'))
    vi.mocked(analysesApi.getAnalysisProgress).mockImplementation(
      () => new Promise(() => undefined),
    )
    render(
      <ProcessingStatus
        analysisId="analysis-1"
        initialState="queued"
        questionPreparationMode="structured_template"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /start analysis/i }))

    await screen.findByText('Validating files', { selector: 'strong' })
    expect(analysesApi.runAnalysis).toHaveBeenCalledWith(
      'analysis-1',
      'structured_template',
    )
  })

  it('polls immediately and stops once a terminal stage is reached', async () => {
    vi.mocked(analysesApi.getAnalysisProgress)
      .mockResolvedValueOnce(progressResponse('extracting_exam'))
      .mockResolvedValueOnce(progressResponse('completed'))

    render(
      <ProcessingStatus
        analysisId="analysis-1"
        initialState="validating"
        pollIntervalMs={10}
      />,
    )

    await screen.findByText('Extracting questions', { selector: 'strong' })
    await screen.findByText('Generating results', { selector: 'strong' })
    const callsAtCompletion = vi.mocked(analysesApi.getAnalysisProgress).mock.calls.length
    await new Promise((resolve) => setTimeout(resolve, 40))
    expect(analysesApi.getAnalysisProgress).toHaveBeenCalledTimes(callsAtCompletion)
  })

  it('stops at review_ready and presents the extraction-review handoff', async () => {
    vi.mocked(analysesApi.getAnalysisProgress).mockResolvedValue(
      progressResponse('review_ready', 'Extraction is ready for review.'),
    )

    render(
      <ProcessingStatus
        analysisId="analysis-1"
        initialState="extracting_tp153"
        pollIntervalMs={10}
      />,
    )

    expect(await screen.findByText('Extracting questions', { selector: 'strong' }))
      .toBeInTheDocument()
    expect(
      screen.getByText('Extraction ready for review', {
        selector: '.ui-alert-title',
      }),
    ).toBeInTheDocument()
    expect(screen.getByText(/continue to the dedicated review workspace/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /confirm|save|restore|exclude/i }))
      .not.toBeInTheDocument()

    const callsAtReviewReady = vi.mocked(analysesApi.getAnalysisProgress).mock.calls.length
    await new Promise((resolve) => setTimeout(resolve, 30))
    expect(analysesApi.getAnalysisProgress).toHaveBeenCalledTimes(callsAtReviewReady)
  })

  it('does not poll when review_ready is loaded directly', async () => {
    render(<ProcessingStatus analysisId="analysis-1" initialState="review_ready" />)

    expect(
      screen.getByText('Extraction ready for review', {
        selector: '.ui-alert-title',
      }),
    ).toBeInTheDocument()
    expect(analysesApi.getAnalysisProgress).not.toHaveBeenCalled()
  })

  it('shows degraded connectivity while retrying and clears it after recovery', async () => {
    vi.mocked(analysesApi.getAnalysisProgress)
      .mockRejectedValueOnce(new ApiError(503, 'Unavailable'))
      .mockResolvedValueOnce(progressResponse('applying_rules'))
      .mockResolvedValue(progressResponse('completed'))

    render(
      <ProcessingStatus
        analysisId="analysis-1"
        initialState="retrieving_knowledge"
        pollIntervalMs={50}
      />,
    )

    expect(await screen.findByText(/polling will retry automatically/i)).toBeInTheDocument()
    await screen.findByText('Applying evaluation criteria', { selector: 'strong' })
    await waitFor(() =>
      expect(screen.queryByText(/polling will retry automatically/i)).not.toBeInTheDocument(),
    )
  })

  it('shows the API-derived failure message without placing failed in the linear stepper', async () => {
    vi.mocked(analysesApi.getAnalysisProgress).mockResolvedValue(
      progressResponse(
        'failed',
        'Processing failed due to an internal error. Please try again later.',
      ),
    )

    render(
      <ProcessingStatus
        analysisId="analysis-1"
        initialState="applying_rules"
        pollIntervalMs={10}
      />,
    )

    expect(await screen.findByText(/examination could not be extracted/i))
      .toBeInTheDocument()
    expect(screen.getByText('Extracting questions', { selector: 'strong' })).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: /analysis processing progress/i }))
      .not.toBeInTheDocument()
  })

  it('retrieves failure details once when a failed progress route is refreshed', async () => {
    vi.mocked(analysesApi.getAnalysisProgress).mockResolvedValue(
      progressResponse('failed', 'The analysis could not be completed.'),
    )

    render(
      <ProcessingStatus
        analysisId="analysis-1"
        initialState="failed"
        pollIntervalMs={10}
      />,
    )

    expect(await screen.findByText(/examination could not be extracted/i)).toBeInTheDocument()
    expect(analysesApi.getAnalysisProgress).toHaveBeenCalledTimes(1)
    await new Promise((resolve) => setTimeout(resolve, 30))
    expect(analysesApi.getAnalysisProgress).toHaveBeenCalledTimes(1)
  })

  it('retries a failed analysis without re-uploading files and resumes polling', async () => {
    vi.mocked(analysesApi.getAnalysisProgress)
      .mockResolvedValueOnce(progressResponse('failed', 'The examination could not be extracted.'))
      .mockResolvedValueOnce(progressResponse('completed'))
    vi.mocked(analysesApi.retryAnalysis).mockResolvedValue(analysisResponse('extracting_exam'))

    render(
      <ProcessingStatus
        analysisId="analysis-1"
        initialState="failed"
        pollIntervalMs={10}
      />,
    )

    const retryButton = await screen.findByRole('button', { name: /retry analysis/i })
    fireEvent.click(retryButton)

    expect(analysesApi.retryAnalysis).toHaveBeenCalledWith('analysis-1')
    expect(await screen.findByText('Generating results', { selector: 'strong' })).toBeInTheDocument()
  })

  it('keeps the explicit start action available after a start error', async () => {
    vi.mocked(analysesApi.runAnalysis).mockRejectedValue(
      new ApiError(500, 'Server unavailable.'),
    )
    render(<ProcessingStatus analysisId="analysis-1" initialState="queued" />)

    fireEvent.click(screen.getByRole('button', { name: /start analysis/i }))

    expect(await screen.findByText(/server unavailable/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument()
  })

  it('notifies the route adapter when the tracked backend state changes', async () => {
    vi.mocked(analysesApi.getAnalysisProgress).mockResolvedValue(
      progressResponse('generating_report'),
    )
    const onStateChange = vi.fn()

    render(
      <ProcessingStatus
        analysisId="analysis-1"
        initialState="applying_rules"
        pollIntervalMs={100}
        onStateChange={onStateChange}
      />,
    )

    await screen.findByText('Generating results', { selector: 'strong' })
    expect(onStateChange).toHaveBeenCalledWith('generating_report')
  })
})
