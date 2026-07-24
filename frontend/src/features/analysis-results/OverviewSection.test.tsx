import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { AnalysisResponse, AnalysisScoreResponse } from '../../types/api'
import { OverviewSection } from './OverviewSection'

vi.mock('../../api/analyses')

const ANALYSIS: AnalysisResponse = {
  id: 'analysis-1',
  course: { id: 'course-1', code: 'CPIT-450', name: 'Software Engineering', department: null, program: null },
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

describe('OverviewSection', () => {
  it('shows the score, denominator, and all five status counts', () => {
    const score: AnalysisScoreResponse = {
      analysis_id: 'analysis-1',
      score: '75.00',
      label: null,
      denominator: 4,
      satisfied_count: 2,
      partially_satisfied_count: 1,
      not_satisfied_count: 1,
      not_verified_count: 1,
      not_applicable_count: 0,
    }
    render(<OverviewSection analysis={ANALYSIS} score={score} />)

    expect(screen.getByText('75.00')).toBeInTheDocument()
    expect(screen.getByText(/based on 4 verified applicable rules/i)).toBeInTheDocument()
    expect(screen.getByText(/satisfied: 2/i)).toBeInTheDocument()
    expect(screen.getByText(/not verified: 1/i)).toBeInTheDocument()
    expect(screen.getByText(/not applicable: 0/i)).toBeInTheDocument()
  })

  it('shows Insufficient Evidence instead of a number when the denominator is zero', () => {
    const score: AnalysisScoreResponse = {
      analysis_id: 'analysis-1',
      score: null,
      label: 'Insufficient Evidence',
      denominator: 0,
      satisfied_count: 0,
      partially_satisfied_count: 0,
      not_satisfied_count: 0,
      not_verified_count: 0,
      not_applicable_count: 0,
    }
    render(<OverviewSection analysis={ANALYSIS} score={score} />)

    expect(screen.getByText('Insufficient Evidence')).toBeInTheDocument()
    expect(screen.queryByText(/overall exam quality score/i)).not.toBeInTheDocument()
  })

  it('uses singular wording for a denominator of one', () => {
    const score: AnalysisScoreResponse = {
      analysis_id: 'analysis-1',
      score: '100.00',
      label: null,
      denominator: 1,
      satisfied_count: 1,
      partially_satisfied_count: 0,
      not_satisfied_count: 0,
      not_verified_count: 0,
      not_applicable_count: 0,
    }
    render(<OverviewSection analysis={ANALYSIS} score={score} />)
    expect(screen.getByText(/based on 1 verified applicable rule\)/i)).toBeInTheDocument()
  })

  const zeroScore: AnalysisScoreResponse = {
    analysis_id: 'analysis-1',
    score: null,
    label: 'Insufficient Evidence',
    denominator: 0,
    satisfied_count: 0,
    partially_satisfied_count: 0,
    not_satisfied_count: 0,
    not_verified_count: 0,
    not_applicable_count: 0,
  }

  it('shows a reanalysis notice only when the analysis has a predecessor', () => {
    render(
      <OverviewSection
        analysis={{ ...ANALYSIS, predecessor_analysis_id: 'analysis-0' }}
        score={zeroScore}
      />,
    )
    expect(screen.getByText(/linked to a previous analysis/i)).toBeInTheDocument()
  })

  it('does not show a reanalysis notice for an analysis with no predecessor', () => {
    render(<OverviewSection analysis={ANALYSIS} score={zeroScore} />)
    expect(screen.queryByText(/linked to a previous analysis/i)).not.toBeInTheDocument()
  })

  it('only renders the Create Reanalysis action when onReanalysisCreated is provided', () => {
    render(<OverviewSection analysis={ANALYSIS} score={zeroScore} />)
    expect(screen.queryByRole('button', { name: /create reanalysis/i })).not.toBeInTheDocument()
  })

  it('renders the Create Reanalysis action when onReanalysisCreated is provided', () => {
    render(
      <OverviewSection analysis={ANALYSIS} score={zeroScore} onReanalysisCreated={vi.fn()} />,
    )
    expect(screen.getByRole('button', { name: /create reanalysis/i })).toBeInTheDocument()
  })
})
