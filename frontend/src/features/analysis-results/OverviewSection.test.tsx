import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { AnalysisResponse, AnalysisScoreResponse } from '../../types/api'
import { OverviewSection } from './OverviewSection'

vi.mock('../../api/analyses')

const ANALYSIS: AnalysisResponse = {
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
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function score(overrides: Partial<AnalysisScoreResponse> = {}): AnalysisScoreResponse {
  return {
    analysis_id: 'analysis-1',
    score: '75.00',
    label: null,
    denominator: 4,
    satisfied_count: 2,
    partially_satisfied_count: 1,
    not_satisfied_count: 1,
    not_verified_count: 1,
    not_applicable_count: 0,
    ...overrides,
  }
}

describe('OverviewSection', () => {
  it('shows the backend score, denominator, and all five approved status counts', () => {
    render(<OverviewSection analysis={ANALYSIS} score={score()} />)

    expect(screen.getByText('75.00%')).toBeInTheDocument()
    expect(screen.getByText(/contains 4 verified applicable rules/i)).toBeInTheDocument()
    expect(screen.getByText('Satisfied').closest('li')).toHaveTextContent('2')
    expect(screen.getByText('Partially Satisfied').closest('li')).toHaveTextContent('1')
    expect(screen.getByText('Not Satisfied').closest('li')).toHaveTextContent('1')
    expect(screen.getByText('Not Verified').closest('li')).toHaveTextContent('1')
    expect(screen.getByText('Not Applicable').closest('li')).toHaveTextContent('0')
  })

  it('shows Insufficient Evidence instead of a number when the score is null', () => {
    render(
      <OverviewSection
        analysis={ANALYSIS}
        score={score({
          score: null,
          label: 'Insufficient Evidence',
          denominator: 0,
        })}
      />,
    )

    expect(screen.getByText('Insufficient Evidence')).toBeInTheDocument()
    expect(screen.queryByText(/0%/)).not.toBeInTheDocument()
  })

  it('renders reanalysis only when the current analysis supplies the contextual action', () => {
    const { rerender } = render(
      <OverviewSection analysis={ANALYSIS} score={score()} />,
    )
    expect(screen.queryByRole('button', { name: /create reanalysis/i }))
      .not.toBeInTheDocument()

    rerender(
      <OverviewSection
        analysis={ANALYSIS}
        score={score()}
        onReanalysisCreated={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: /create reanalysis/i }))
      .toBeInTheDocument()
    expect(screen.getByText('analysis-1')).toBeInTheDocument()
  })
})
