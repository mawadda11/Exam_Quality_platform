import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { AnalysisResponse, ProgressResponse } from '../../types/api'
import { ProcessingStatus } from './ProcessingStatus'

vi.mock('../../api/analyses')

beforeEach(() => {
  vi.mocked(analysesApi.runAnalysis).mockReset()
  vi.mocked(analysesApi.getAnalysisProgress).mockReset()
})

function analysisResponse(state: AnalysisResponse['state']): AnalysisResponse {
  return {
    id: 'analysis-1',
    course: { id: 'course-1', code: 'CPIT-450', name: 'SE', department: null, program: null },
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
  return { analysis_id: 'analysis-1', state, message, updated_at: '2026-01-01T00:00:00Z' }
}

describe('ProcessingStatus', () => {
  it('shows a Start analysis button when the analysis is still queued', () => {
    render(<ProcessingStatus analysisId="analysis-1" initialState="queued" />)
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument()
    expect(screen.queryByText(/current stage/i)).not.toBeInTheDocument()
  })

  it('starts the analysis and shows the returned stage', async () => {
    vi.mocked(analysesApi.runAnalysis).mockResolvedValue(analysisResponse('validating'))
    render(<ProcessingStatus analysisId="analysis-1" initialState="queued" pollIntervalMs={10} />)

    fireEvent.click(screen.getByRole('button', { name: /start analysis/i }))

    expect(await screen.findByText(/current stage/i)).toBeInTheDocument()
    expect(screen.getByText('Validating')).toBeInTheDocument()
    expect(analysesApi.runAnalysis).toHaveBeenCalledWith('analysis-1')
  })

  it('polls progress and stops once a terminal stage is reached', async () => {
    vi.mocked(analysesApi.getAnalysisProgress)
      .mockResolvedValueOnce(progressResponse('extracting_exam'))
      .mockResolvedValueOnce(progressResponse('completed'))
      .mockResolvedValue(progressResponse('completed'))

    render(
      <ProcessingStatus analysisId="analysis-1" initialState="validating" pollIntervalMs={10} />,
    )

    await screen.findByText('Extracting exam')
    await screen.findByText('Completed')

    const callCountAtCompletion = vi.mocked(analysesApi.getAnalysisProgress).mock.calls.length
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(analysesApi.getAnalysisProgress).toHaveBeenCalledTimes(callCountAtCompletion)
  })

  it('shows the safe failure message when progress reports failed', async () => {
    vi.mocked(analysesApi.getAnalysisProgress).mockResolvedValue(
      progressResponse('failed', 'Processing failed due to an internal error. Please try again later.'),
    )

    render(
      <ProcessingStatus analysisId="analysis-1" initialState="applying_rules" pollIntervalMs={10} />,
    )

    expect(await screen.findByText(/processing failed due to an internal error/i)).toBeInTheDocument()
  })

  it('shows a start error without changing the displayed stage', async () => {
    vi.mocked(analysesApi.runAnalysis).mockRejectedValue(new ApiError(500, 'Server unavailable.'))
    render(<ProcessingStatus analysisId="analysis-1" initialState="queued" />)

    fireEvent.click(screen.getByRole('button', { name: /start analysis/i }))

    expect(await screen.findByText(/server unavailable/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument()
  })

  it('calls onStateChange whenever the tracked stage changes, so a parent can react to completion', async () => {
    vi.mocked(analysesApi.runAnalysis).mockResolvedValue(analysisResponse('validating'))
    const onStateChange = vi.fn()
    render(
      <ProcessingStatus
        analysisId="analysis-1"
        initialState="queued"
        onStateChange={onStateChange}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /start analysis/i }))

    await screen.findByText('Validating')
    expect(onStateChange).toHaveBeenCalledWith('validating')
  })
})
