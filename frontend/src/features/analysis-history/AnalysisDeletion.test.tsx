import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import type { AnalysisResponse } from '../../types/api'
import { AnalysisHistoryTable } from './AnalysisHistoryTable'

vi.mock('../../api/analyses')

function analysis(overrides: Partial<AnalysisResponse> = {}): AnalysisResponse {
  return {
    id: 'analysis-1',
    course: {
      id: 'course-1',
      code: 'CPIT-425',
      name: 'Information Security',
      department: null,
      program: null,
    },
    exam_type: 'Final',
    term: '2026 Spring',
    state: 'completed',
    owner_user_id: 'user-1',
    predecessor_analysis_id: null,
    uploaded_files: [],
    exam_uploaded: true,
    tp153_uploaded: true,
    ready_for_analysis: true,
    created_at: '2026-08-01T00:00:00Z',
    updated_at: '2026-08-01T00:00:00Z',
    ...overrides,
  }
}

function Harness({ initial = analysis() }: { initial?: AnalysisResponse }) {
  const [items, setItems] = useState([initial])
  return (
    <MemoryRouter>
      <AnalysisHistoryTable
        analyses={items}
        caption="All analyses"
        onDeleted={(id) => setItems((current) => current.filter((item) => item.id !== id))}
      />
    </MemoryRouter>
  )
}

describe('analysis deletion confirmation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(analysesApi.deleteAnalysis).mockResolvedValue()
  })

  it('shows source-faithful context and cancel does not delete', () => {
    render(<Harness />)
    fireEvent.click(screen.getByRole('button', { name: 'Delete analysis' }))
    expect(screen.getByRole('dialog', { name: 'Permanently delete analysis?' })).toHaveTextContent(
      'CPIT-425',
    )
    expect(screen.getByRole('dialog')).toHaveTextContent('Information Security')
    expect(screen.getByRole('dialog')).toHaveTextContent('2026 Spring')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(analysesApi.deleteAnalysis).not.toHaveBeenCalled()
  })

  it('confirms once and removes the item without reloading', async () => {
    render(<Harness />)
    fireEvent.click(screen.getByRole('button', { name: 'Delete analysis' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete permanently' }))
    await waitFor(() => expect(analysesApi.deleteAnalysis).toHaveBeenCalledOnce())
    expect(analysesApi.deleteAnalysis).toHaveBeenCalledWith('analysis-1')
    await waitFor(() => expect(screen.queryByText('CPIT-425')).not.toBeInTheDocument())
  })

  it('preserves the item on failure and disables deletion for active processing', async () => {
    vi.mocked(analysesApi.deleteAnalysis).mockRejectedValue(new Error('failed'))
    const { unmount } = render(<Harness />)
    fireEvent.click(screen.getByRole('button', { name: 'Delete analysis' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete permanently' }))
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getAllByText('CPIT-425').length).toBeGreaterThan(0)
    unmount()

    render(<Harness initial={analysis({ state: 'applying_rules' })} />)
    expect(screen.getByRole('button', { name: 'Delete analysis' })).toBeDisabled()
  })
})
