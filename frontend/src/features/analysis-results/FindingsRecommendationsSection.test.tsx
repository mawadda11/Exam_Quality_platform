import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { FindingResponse, RecommendationResponse } from '../../types/api'
import { FindingsRecommendationsSection } from './FindingsRecommendationsSection'
import { buildLookups } from './lookups'

function finding(overrides: Partial<FindingResponse>): FindingResponse {
  return {
    id: 'finding-1',
    analysis_id: 'analysis-1',
    requirement_id: 'REQ001',
    rule_id: 'RULE001',
    status: 'Satisfied',
    explanation: 'Every scorable question cites an explicit CLO reference.',
    confidence: 1,
    evaluator_type: 'deterministic_rule',
    created_at: '2026-01-01T00:00:00Z',
    evidence: [],
    requirement_name: 'Question-to-CLO Mapping',
    dimension: 'CLO Alignment',
    source_type: 'Derived Exam Requirement',
    officiality: 'Derived',
    ...overrides,
  }
}

const LOOKUPS = buildLookups([], [], [])

describe('FindingsRecommendationsSection', () => {
  it('calls out Not Verified findings in a separate Missing Evidence panel', () => {
    const findings = [
      finding({ id: 'f-ok', status: 'Satisfied' }),
      finding({
        id: 'f-missing',
        status: 'Not Verified',
        requirement_name: 'Applicable CLO Coverage',
        explanation: 'No CLOs were extracted from the TP-153.',
      }),
    ]
    render(
      <FindingsRecommendationsSection
        findings={findings}
        recommendationsByFinding={new Map()}
        lookups={LOOKUPS}
      />,
    )

    const panel = screen.getByText(/missing evidence \(1\)/i).closest('div') as HTMLElement
    expect(within(panel).getByText(/no clos were extracted from the tp-153\./i)).toBeInTheDocument()
  })

  it('does not render a Missing Evidence panel when there are no Not Verified findings', () => {
    render(
      <FindingsRecommendationsSection
        findings={[finding({ status: 'Satisfied' })]}
        recommendationsByFinding={new Map()}
        lookups={LOOKUPS}
      />,
    )
    expect(screen.queryByText(/missing evidence/i)).not.toBeInTheDocument()
  })

  it('renders the recommendation attached to its finding', () => {
    const target = finding({ id: 'f-partial', status: 'Partially Satisfied' })
    const recommendation: RecommendationResponse = {
      finding_id: 'f-partial',
      requirement_id: 'REQ001',
      rule_id: 'RULE001',
      status: 'Partially Satisfied',
      recommendation_id: 'REC001',
      title: 'Map the Question to a CLO',
      text: 'Review the question and assign it to at least one supported course learning outcome.',
      target_user: 'Faculty and Course Coordinator',
      recommendation_type: 'Corrective',
    }
    render(
      <FindingsRecommendationsSection
        findings={[target]}
        recommendationsByFinding={new Map([['f-partial', [recommendation]]])}
        lookups={LOOKUPS}
      />,
    )

    expect(screen.getByText('Map the Question to a CLO')).toBeInTheDocument()
    expect(screen.getByText(/for: faculty and course coordinator/i)).toBeInTheDocument()
  })

  it('shows an honest empty state when there are no findings at all', () => {
    render(
      <FindingsRecommendationsSection findings={[]} recommendationsByFinding={new Map()} lookups={LOOKUPS} />,
    )
    expect(screen.getByText(/findings are not available yet/i)).toBeInTheDocument()
  })
})
