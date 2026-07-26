import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { FindingResponse, RecommendationResponse } from '../../types/api'
import { FindingsRecommendationsSection } from './FindingsRecommendationsSection'
import { buildLookups } from './lookups'

function finding(overrides: Partial<FindingResponse>): FindingResponse {
  return {
    id: 'finding-1',
    analysis_id: 'analysis-1',
    requirement_id: 'REQ001',
    rule_id: 'RULE001',
    recommendation_id: null,
    status: 'Satisfied',
    explanation: 'Every scorable question cites an explicit CLO reference.',
    confidence: 1,
    evaluator_type: 'deterministic_rule',
    ai_provider: null,
    ai_model: null,
    prompt_template_version: null,
    kb_version: null,
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

function renderSection(
  findings: FindingResponse[],
  recommendations: RecommendationResponse[] = [],
) {
  const byFinding = new Map<string, RecommendationResponse[]>()
  for (const recommendation of recommendations) {
    byFinding.set(recommendation.finding_id, [recommendation])
  }
  render(
    <FindingsRecommendationsSection
      findings={findings}
      recommendations={{ status: 'ready', data: recommendations }}
      recommendationsByFinding={byFinding}
      lookups={LOOKUPS}
      onRetryRecommendations={vi.fn()}
    />,
  )
}

describe('FindingsRecommendationsSection', () => {
  it('calls out filtered Not Verified findings as Missing Evidence', () => {
    renderSection([
      finding({ id: 'f-ok', status: 'Satisfied' }),
      finding({
        id: 'f-missing',
        status: 'Not Verified',
        requirement_name: 'Applicable CLO Coverage',
        explanation: 'No CLOs were extracted from the TP-153.',
      }),
    ])

    const panel = screen.getByText(/missing evidence \(1\)/i).closest('div') as HTMLElement
    expect(within(panel).getByText(/no clos were extracted/i)).toBeInTheDocument()
  })

  it('renders a recommendation attached to its finding', () => {
    const target = finding({ id: 'f-partial', status: 'Partially Satisfied' })
    const recommendation: RecommendationResponse = {
      finding_id: 'f-partial',
      requirement_id: 'REQ001',
      rule_id: 'RULE001',
      status: 'Partially Satisfied',
      recommendation_id: 'REC001',
      title: 'Map the Question to a CLO',
      text: 'Review the existing evidence.',
      target_user: 'Faculty',
      recommendation_type: 'Corrective',
    }
    renderSection([target], [recommendation])

    expect(screen.getByText('Map the Question to a CLO')).toBeInTheDocument()
    expect(screen.getByText(/for: faculty/i)).toBeInTheDocument()
  })

  it('keeps findings visible while a recommendation request is unavailable', () => {
    render(
      <FindingsRecommendationsSection
        findings={[finding({})]}
        recommendations={{ status: 'error', message: 'Recommendations unavailable.' }}
        recommendationsByFinding={new Map()}
        lookups={LOOKUPS}
        onRetryRecommendations={vi.fn()}
      />,
    )

    expect(screen.getByText('Question-to-CLO Mapping')).toBeInTheDocument()
    expect(screen.getByText(/recommendations unavailable/i)).toBeInTheDocument()
  })

  it('shows an honest empty state when there are no findings', () => {
    renderSection([])
    expect(screen.getByText(/no findings are available/i)).toBeInTheDocument()
  })
})
