import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { AnalysisResponse } from '../../types/api'
import { ReanalysisAction } from './ReanalysisAction'

vi.mock('../../api/analyses')

const REANALYSIS: AnalysisResponse = {
  id: 'analysis-2',
  course: { id: 'course-1', code: 'CPIT-450', name: 'Software Engineering', department: null, program: null },
  exam_type: 'Midterm',
  term: '2026 Spring',
  state: 'queued',
  owner_user_id: 'user-1',
  predecessor_analysis_id: 'analysis-1',
  uploaded_files: [],
  exam_uploaded: false,
  tp153_uploaded: true,
  ready_for_analysis: false,
  created_at: '2026-07-24T00:00:00Z',
  updated_at: '2026-07-24T00:00:00Z',
}

beforeEach(() => {
  vi.mocked(analysesApi.createReanalysis).mockReset()
})

describe('ReanalysisAction', () => {
  it('defaults to reusing the previous TP-153', () => {
    render(<ReanalysisAction analysisId="analysis-1" onCreated={vi.fn()} />)
    expect(screen.getByRole('checkbox', { name: /reuse the previous tp-153/i })).toBeChecked()
  })

  it('creates a reanalysis with reuse_tp153 true by default and reports it back', async () => {
    vi.mocked(analysesApi.createReanalysis).mockResolvedValue(REANALYSIS)
    const onCreated = vi.fn()

    render(<ReanalysisAction analysisId="analysis-1" onCreated={onCreated} />)
    fireEvent.click(screen.getByRole('button', { name: /create reanalysis/i }))

    await vi.waitFor(() => {
      expect(analysesApi.createReanalysis).toHaveBeenCalledWith('analysis-1', {
        reuse_tp153: true,
      })
    })
    expect(onCreated).toHaveBeenCalledWith(REANALYSIS)
  })

  it('creates a reanalysis with reuse_tp153 false when unchecked', async () => {
    vi.mocked(analysesApi.createReanalysis).mockResolvedValue(REANALYSIS)

    render(<ReanalysisAction analysisId="analysis-1" onCreated={vi.fn()} />)
    fireEvent.click(screen.getByRole('checkbox', { name: /reuse the previous tp-153/i }))
    fireEvent.click(screen.getByRole('button', { name: /create reanalysis/i }))

    await vi.waitFor(() => {
      expect(analysesApi.createReanalysis).toHaveBeenCalledWith('analysis-1', {
        reuse_tp153: false,
      })
    })
  })

  it('shows an error message when creation fails, without calling onCreated', async () => {
    vi.mocked(analysesApi.createReanalysis).mockRejectedValue(
      new ApiError(409, 'Only a completed analysis can be reanalyzed.'),
    )
    const onCreated = vi.fn()

    render(<ReanalysisAction analysisId="analysis-1" onCreated={onCreated} />)
    fireEvent.click(screen.getByRole('button', { name: /create reanalysis/i }))

    expect(await screen.findByText(/only a completed analysis can be reanalyzed/i)).toBeInTheDocument()
    expect(onCreated).not.toHaveBeenCalled()
  })
})
