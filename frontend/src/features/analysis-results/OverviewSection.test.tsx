import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { AnalysisScoreResponse, RuleCoverageAuditResponse } from '../../types/api'
import { OverviewSection } from './OverviewSection'

vi.mock('../../api/analyses')

const RULE_COVERAGE: RuleCoverageAuditResponse = {
  analysis_id: 'analysis-1',
  scope: 'exam_facing_rules',
  total_rules: 21,
  evaluated_rules: 14,
  conditional_capability_gap_rules: 1,
  unsupported_rules: 6,
  not_run_rules: 0,
  runtime_integrity_ok: true,
  entries: [],
}

const COVERAGE_RESOURCE = { status: 'ready' as const, data: RULE_COVERAGE }

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

function renderOverview(props: { score?: AnalysisScoreResponse } = {}) {
  return render(
    <MemoryRouter>
      <OverviewSection
        score={props.score ?? score()}
        ruleCoverage={COVERAGE_RESOURCE}
        onRetryRuleCoverage={vi.fn()}
      />
    </MemoryRouter>,
  )
}

describe('OverviewSection', () => {
  it('shows the score and academic statuses without exposing an arithmetic formula', () => {
    renderOverview()

    expect(screen.getByText('75.00%')).toBeInTheDocument()
    expect(screen.getByText('Based on 4 verified checks')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'About this score' })).toBeInTheDocument()
    expect(screen.getByText(
      'This is an advisory estimate of exam quality based on the criteria that could be verified. It is not the exam mark or a student pass rate.',
    )).toBeInTheDocument()
    expect(screen.queryByText(/earned credit/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/× 1\.0/i)).not.toBeInTheDocument()
    expect(screen.getByText(/analysis completed with a limited check/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /see what the platform evaluates/i }))
      .toHaveAttribute('href', '/evaluation-scope')
    expect(screen.getByRole('link', { name: /learn how this works/i }))
      .toHaveAttribute('href', '/evaluation-scope#overall-score')
    const evaluationHeading = screen.getByRole('heading', { name: 'Evaluation results' })
    const scoreText = screen.getByText('75.00%')
    expect(evaluationHeading.compareDocumentPosition(scoreText) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByText('Satisfied').closest('li')).toHaveTextContent('2')
    expect(screen.getByText('Partially Satisfied').closest('li')).toHaveTextContent('1')
    expect(screen.getByText('Not Satisfied').closest('li')).toHaveTextContent('1')
    expect(screen.getByText('Not Verified').closest('li')).toHaveTextContent('1')
    expect(screen.getByText('Not Applicable').closest('li')).toHaveTextContent('0')
  })

  it('shows Insufficient Evidence instead of a number when the score is null', () => {
    renderOverview({
      score: score({
        score: null,
        label: 'Insufficient Evidence',
        denominator: 0,
      }),
    })

    expect(screen.getByText('Insufficient Evidence')).toBeInTheDocument()
    expect(screen.queryByText(/0%/)).not.toBeInTheDocument()
  })
})
