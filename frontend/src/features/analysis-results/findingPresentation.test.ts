import { describe, expect, it } from 'vitest'
import type { AcademicStatus, FindingResponse } from '../../types/api'
import {
  scoreImpactMessage,
  sectionDestinationForFinding,
  sortFindingsForFaculty,
} from './findingPresentation'

describe('scoreImpactMessage', () => {
  it.each<[AcademicStatus, string]>([
    ['Satisfied', 'Included fully in the score.'],
    ['Partially Satisfied', 'Included with partial credit.'],
    ['Not Satisfied', 'Included as an unmet requirement.'],
    [
      'Not Verified',
      'Excluded because the evidence was insufficient for a reliable judgment.',
    ],
    [
      'Not Applicable',
      'Excluded because the requirement does not apply to this analysis.',
    ],
  ])('uses the approved wording for %s', (status, expected) => {
    expect(scoreImpactMessage(status)).toBe(expected)
  })
})

function finding(
  status: AcademicStatus,
  overrides: Partial<FindingResponse> = {},
): FindingResponse {
  return {
    id: status,
    analysis_id: 'analysis-1',
    requirement_id: 'REQ001',
    rule_id: 'RULE001',
    recommendation_id: null,
    status,
    explanation: 'Result explanation.',
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

describe('faculty finding order and destinations', () => {
  it('uses the approved attention order', () => {
    expect(
      sortFindingsForFaculty([
        finding('Not Verified'),
        finding('Partially Satisfied'),
        finding('Not Satisfied'),
      ]).map((item) => item.status),
    ).toEqual(['Not Satisfied', 'Partially Satisfied', 'Not Verified'])
  })

  it('links findings to their specialized academic page', () => {
    expect(sectionDestinationForFinding(finding('Satisfied'))?.section)
      .toBe('alignment-coverage')
    expect(
      sectionDestinationForFinding(
        finding('Satisfied', {
          rule_id: 'RULE018',
          dimension: 'Marks and Totals',
        }),
      )?.section,
    ).toBe('marks-structure')
    expect(
      sectionDestinationForFinding(
        finding('Satisfied', {
          rule_id: 'RULE014',
          dimension: 'Supporting Materials',
        }),
      )?.section,
    ).toBe('supporting-evidence')
  })
})
