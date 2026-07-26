import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { FindingResponse } from '../../types/api'
import { buildLookups } from './lookups'
import { MarksStructureSection } from './MarksStructureSection'

function finding(dimension: string, name: string): FindingResponse {
  return {
    id: name,
    analysis_id: 'analysis-1',
    requirement_id: 'REQ001',
    rule_id: 'RULE001',
    recommendation_id: null,
    status: 'Satisfied',
    explanation: 'Existing backend explanation.',
    confidence: 1,
    confidence_level: null,
    evaluation_details: null,
    evaluator_type: 'deterministic_rule',
    ai_provider: null,
    ai_model: null,
    prompt_template_version: null,
    kb_version: null,
    created_at: '2026-01-01T00:00:00Z',
    evidence: [],
    requirement_name: name,
    dimension,
    source_type: 'Derived Exam Requirement',
    officiality: 'Derived',
  }
}

describe('MarksStructureSection', () => {
  it('shows only existing marks and structure findings without deriving totals', () => {
    render(
      <MarksStructureSection
        findings={[
          finding('Marks and Totals', 'Correct Total Marks'),
          finding('CLO Alignment', 'CLO Mapping'),
        ]}
        lookups={buildLookups([], [], [])}
      />,
    )

    expect(screen.getByText('Correct Total Marks')).toBeInTheDocument()
    expect(screen.queryByText('CLO Mapping')).not.toBeInTheDocument()
    expect(screen.queryByText(/calculated total/i)).not.toBeInTheDocument()
  })
})
