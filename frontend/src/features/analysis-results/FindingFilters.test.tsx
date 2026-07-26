import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { FindingResponse } from '../../types/api'
import {
  EMPTY_FINDING_FILTERS,
  filterFindings,
} from './findingFilterModel'
import { FindingFilters } from './FindingFilters'

function finding(overrides: Partial<FindingResponse>): FindingResponse {
  return {
    id: 'finding-1',
    analysis_id: 'analysis-1',
    requirement_id: 'REQ001',
    rule_id: 'RULE001',
    recommendation_id: null,
    status: 'Satisfied',
    explanation: 'Explanation',
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
    requirement_name: 'Requirement',
    dimension: 'CLO Alignment',
    source_type: 'Derived Exam Requirement',
    officiality: 'Derived',
    ...overrides,
  }
}

const FINDINGS = [
  finding({
    id: 'f-1',
    evidence: [
      {
        id: 'ev-1',
        source_document: 'exam',
        evidence_type: 'question_text',
        page_number: 1,
        item_reference: 'Q1',
      },
    ],
  }),
  finding({
    id: 'f-2',
    status: 'Not Verified',
    dimension: 'Topic Coverage',
  }),
]

describe('FindingFilters', () => {
  it('filters already-loaded findings by status, dimension, and cited question', () => {
    expect(
      filterFindings(FINDINGS, {
        status: 'Satisfied',
        dimension: 'CLO Alignment',
        question: 'Q1',
      }),
    ).toEqual([FINDINGS[0]])
    expect(
      filterFindings(FINDINGS, {
        status: 'all',
        dimension: 'all',
        question: 'Q9',
      }),
    ).toEqual([])
  })

  it('offers only values present in loaded findings and resets filters', () => {
    const onChange = vi.fn()
    render(
      <FindingFilters
        findings={FINDINGS}
        values={{ ...EMPTY_FINDING_FILTERS, status: 'Not Verified' }}
        resultCount={1}
        onChange={onChange}
      />,
    )

    expect(screen.getByRole('option', { name: 'Q1' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Q9' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /reset filters/i }))
    expect(onChange).toHaveBeenCalledWith(EMPTY_FINDING_FILTERS)
  })
})
