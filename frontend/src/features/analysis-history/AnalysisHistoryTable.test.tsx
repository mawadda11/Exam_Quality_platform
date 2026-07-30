import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
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
  afterEach(() => {
    vi.unstubAllGlobals()
  })

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
  })

  it('uses record cards instead of a table at the mobile breakpoint', () => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))

    render(
      <MemoryRouter>
        <AnalysisHistoryTable analyses={[analysis()]} caption="All analyses" />
      </MemoryRouter>,
    )

    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'All analyses' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open analysis' })).toBeInTheDocument()
  })
})
