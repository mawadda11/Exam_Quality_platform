import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

  it('starts after the explicit action and preserves the exact backend stage label', async () => {
    vi.mocked(analysesApi.runAnalysis).mockResolvedValue(analysisResponse('validating'))
    vi.mocked(analysesApi.getAnalysisProgress).mockImplementation(
      () => new Promise(() => undefined),
    )
    render(<ProcessingStatus analysisId="analysis-1" initialState="queued" />)

    fireEvent.click(screen.getByRole('button', { name: /start analysis/i }))

    expect(await screen.findByText('validating', { selector: 'strong' })).toBeInTheDocument()
    expect(analysesApi.runAnalysis).toHaveBeenCalledWith('analysis-1')
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

    await screen.findByText('extracting_exam', { selector: 'strong' })
    await screen.findByText('completed', { selector: 'strong' })
    const callsAtCompletion = vi.mocked(analysesApi.getAnalysisProgress).mock.calls.length
    await new Promise((resolve) => setTimeout(resolve, 40))
    expect(analysesApi.getAnalysisProgress).toHaveBeenCalledTimes(callsAtCompletion)
  })

  it('stops at review_ready and presents a read-only review handoff', async () => {
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

    expect(await screen.findByText('review_ready', { selector: 'strong' }))
      .toBeInTheDocument()
    expect(
      screen.getByText('Extraction ready for review', {
        selector: '.ui-alert-title',
      }),
    ).toBeInTheDocument()
    expect(screen.getByText(/available in a later milestone/i)).toBeInTheDocument()
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
    await screen.findByText('applying_rules', { selector: 'strong' })
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

    expect(await screen.findByText(/processing failed due to an internal error/i))
      .toBeInTheDocument()
    expect(screen.getByText('failed', { selector: 'strong' })).toBeInTheDocument()
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

    expect(await screen.findByText(/analysis could not be completed/i)).toBeInTheDocument()
    expect(analysesApi.getAnalysisProgress).toHaveBeenCalledTimes(1)
    await new Promise((resolve) => setTimeout(resolve, 30))
    expect(analysesApi.getAnalysisProgress).toHaveBeenCalledTimes(1)
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

    await screen.findByText('generating_report', { selector: 'strong' })
    expect(onStateChange).toHaveBeenCalledWith('generating_report')
  })
})
