import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { AnalysisResponse } from '../../types/api'
import { AnalysisHistoryList } from './AnalysisHistoryList'

function analysis(overrides: Partial<AnalysisResponse> = {}): AnalysisResponse {
  return {
    id: 'analysis-1',
    course: {
      id: 'course-1',
      code: 'CPIT-450',
      name: 'Software Engineering',
      department: null,
      program: null,
    },
    exam_type: 'Midterm',
    term: '2026 Spring',
    state: 'completed',
    owner_user_id: 'user-1',
    predecessor_analysis_id: null,
    uploaded_files: [],
    exam_uploaded: true,
    tp153_uploaded: true,
    ready_for_analysis: true,
    created_at: '2026-07-24T00:00:00Z',
    updated_at: '2026-07-24T00:00:00Z',
    ...overrides,
  }
}

describe('AnalysisHistoryList', () => {
  it('lists each analysis with its course, exam type, term, and state', () => {
    render(
      <MemoryRouter>
        <AnalysisHistoryList analyses={[analysis()]} />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('link', { name: /CPIT-450.*Midterm.*2026 Spring/ }),
    ).toBeInTheDocument()
    expect(screen.getByText(/completed/i)).toBeInTheDocument()
  })

  it('marks a reanalysis distinctly from an original analysis', () => {
    render(
      <MemoryRouter>
        <AnalysisHistoryList
          analyses={[analysis({ id: 'analysis-2', predecessor_analysis_id: 'analysis-1' })]}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText(/reanalysis/i)).toBeInTheDocument()
  })

  it('does not show the reanalysis marker for an original analysis', () => {
    render(
      <MemoryRouter>
        <AnalysisHistoryList analyses={[analysis()]} />
      </MemoryRouter>,
    )
    expect(screen.queryByText(/reanalysis/i)).not.toBeInTheDocument()
  })

  it('links a completed analysis to its refresh-safe overview route', () => {
    render(
      <MemoryRouter>
        <AnalysisHistoryList analyses={[analysis({ id: 'analysis-9' })]} />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link')).toHaveAttribute(
      'href',
      '/analyses/analysis-9/results/overview',
    )
  })
})
