import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { AnalysisResponse } from '../../types/api'
import { AnalysisHistoryTable } from './AnalysisHistoryTable'

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

describe('AnalysisHistoryTable', () => {
  it('renders an accessible native table with source-faithful metadata', () => {
    render(
      <MemoryRouter>
        <AnalysisHistoryTable analyses={[analysis()]} caption="All analyses" />
      </MemoryRouter>,
    )

    expect(screen.getByRole('table', { name: 'All analyses' })).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: 'CPIT-450' })).toBeInTheDocument()
    expect(screen.getByText('Software Engineering')).toHaveAttribute('dir', 'auto')
    expect(screen.getByLabelText('Processing state: completed')).toHaveTextContent('completed')
    expect(screen.getByText('Original')).toBeInTheDocument()
  })

  it('marks and routes a linked reanalysis using its backend state', () => {
    render(
      <MemoryRouter>
        <AnalysisHistoryTable
          analyses={[
            analysis({
              id: 'analysis-2',
              state: 'validating',
              predecessor_analysis_id: 'analysis-1',
            }),
          ]}
          caption="Recent analyses"
        />
      </MemoryRouter>,
    )

    expect(screen.getByText('Linked reanalysis')).toBeInTheDocument()
    expect(screen.getByLabelText('Processing state: validating')).toHaveTextContent(
      'validating',
    )
    expect(screen.getByRole('link', { name: 'Open analysis' })).toHaveAttribute(
      'href',
      '/analyses/analysis-2/progress',
    )
  })
})
