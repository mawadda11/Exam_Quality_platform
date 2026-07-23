import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { CloResponse, FindingResponse, TopicResponse } from '../../types/api'
import { AlignmentCoverageSection } from './AlignmentCoverageSection'
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

const CLOS: CloResponse[] = [
  {
    id: 'clo-1',
    analysis_id: 'analysis-1',
    code: 'CLO1',
    text: 'Explain core concepts.',
    program_outcome_reference: null,
    page_number: 1,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
]

const TOPICS: TopicResponse[] = []

describe('AlignmentCoverageSection', () => {
  it('only shows findings whose dimension belongs to Alignment & Coverage', () => {
    const findings = [
      finding({ id: 'f-clo', dimension: 'CLO Alignment', requirement_name: 'Question-to-CLO Mapping' }),
      finding({ id: 'f-marks', dimension: 'Marks and Totals', requirement_name: 'Correct Total Marks' }),
    ]
    render(
      <AlignmentCoverageSection
        findings={findings}
        clos={CLOS}
        topics={TOPICS}
        lookups={buildLookups(CLOS, TOPICS, [])}
      />,
    )

    expect(screen.getByText('Question-to-CLO Mapping')).toBeInTheDocument()
    expect(screen.queryByText('Correct Total Marks')).not.toBeInTheDocument()
  })

  it('shows the honest empty state when no alignment/coverage findings exist yet', () => {
    render(
      <AlignmentCoverageSection findings={[]} clos={[]} topics={[]} lookups={buildLookups([], [], [])} />,
    )
    expect(screen.getByText(/no alignment or coverage findings/i)).toBeInTheDocument()
  })

  it('always shows the raw CLO/topic reference lists alongside the findings', () => {
    render(
      <AlignmentCoverageSection
        findings={[]}
        clos={CLOS}
        topics={TOPICS}
        lookups={buildLookups(CLOS, TOPICS, [])}
      />,
    )
    expect(screen.getByText('CLO1')).toBeInTheDocument()
    expect(screen.getByText('Explain core concepts.')).toBeInTheDocument()
    expect(screen.getByText(/no topics were extracted/i)).toBeInTheDocument()
  })
})
