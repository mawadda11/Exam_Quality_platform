import { describe, expect, it } from 'vitest'
import type { AnalysisScoreResponse, FindingResponse, QuestionResponse } from '../../types/api'
import type { MaterialRelationshipView } from '../analysis-results/materialRelationships'
import {
  buildExamSummary,
  groupFindingsForReport,
  groupRecommendationsForReport,
  marksTotalsFromFindings,
  statusDistributionCounts,
} from './reportPresentation'

function finding(overrides: Partial<FindingResponse>): FindingResponse {
  return {
    id: 'finding-1',
    analysis_id: 'analysis-1',
    requirement_id: 'REQ011',
    rule_id: 'RULE011',
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
    requirement_name: 'Clear Task Statement',
    dimension: 'Question Clarity',
    source_type: 'Derived Exam Requirement',
    officiality: 'Derived',
    ...overrides,
  }
}

function question(overrides: Partial<QuestionResponse> = {}): QuestionResponse {
  return {
    id: 'q-1',
    analysis_id: 'analysis-1',
    parent_question_id: null,
    number_label: 'Q1',
    question_text: 'Text',
    page_number: 1,
    marks: 5,
    sequence: 1,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('marksTotalsFromFindings', () => {
  it('reads declared and calculated totals from the authoritative RULE018 explanation', () => {
    const marksFinding = finding({
      rule_id: 'RULE018',
      dimension: 'Marks and Totals',
      explanation: 'Calculated total marks (40.0) equal the declared total marks (40.0).',
      evidence: [
        {
          id: 'e1',
          source_document: 'exam',
          evidence_type: 'declared_total',
          page_number: 1,
          item_reference: 'total',
        },
      ],
    })

    expect(marksTotalsFromFindings([marksFinding])).toEqual({ declared: 40, calculated: 40 })
  })

  it('supports a governed mismatch explanation without recalculating marks in the frontend', () => {
    const marksFinding = finding({
      rule_id: 'RULE018',
      dimension: 'Marks and Totals',
      explanation: 'Calculated total marks (38) differ from the declared total marks (40).',
    })

    expect(marksTotalsFromFindings([marksFinding])).toEqual({ declared: 40, calculated: 38 })
  })

  it('returns nulls when no RULE018 finding is present', () => {
    expect(marksTotalsFromFindings([finding({})])).toEqual({ declared: null, calculated: null })
  })
})

describe('buildExamSummary', () => {
  it('excludes structural parents from the scorable question count', () => {
    const parent = question({ id: 'parent', number_label: 'Q1', marks: 10 })
    const child = question({
      id: 'child',
      number_label: 'Q1(a)',
      parent_question_id: 'parent',
      marks: 4,
    })
    const summary = buildExamSummary([parent, child], [], 0, [])
    expect(summary.scorableQuestionCount).toBe(1)
  })

  it('counts missing and ambiguous references but not linked or nearby ones', () => {
    const references: MaterialRelationshipView[] = [
      { result: 'linked' } as MaterialRelationshipView,
      { result: 'missing' } as MaterialRelationshipView,
      { result: 'ambiguous' } as MaterialRelationshipView,
      { result: 'nearby' } as MaterialRelationshipView,
    ]
    const summary = buildExamSummary([], [], 3, references)
    expect(summary.missingOrAmbiguousReferenceCount).toBe(2)
    expect(summary.materialCount).toBe(3)
  })
})

describe('groupFindingsForReport', () => {
  it('separates strengths, areas for improvement, and missing evidence', () => {
    const grouped = groupFindingsForReport([
      finding({ id: 'satisfied', status: 'Satisfied' }),
      finding({ id: 'not-satisfied', status: 'Not Satisfied' }),
      finding({ id: 'not-verified', status: 'Not Verified' }),
      finding({ id: 'not-applicable', status: 'Not Applicable' }),
    ])

    expect(grouped.strengths.map((item) => item.id)).toEqual(['satisfied'])
    expect(grouped.areasForImprovement.map((item) => item.id)).toEqual(['not-satisfied'])
    expect(grouped.missingEvidence.map((item) => item.id)).toEqual(['not-verified'])
  })
})

describe('groupRecommendationsForReport', () => {
  it('groups findings with a recommendation by faculty-facing section, deduplicated per requirement', () => {
    const groups = groupRecommendationsForReport([
      finding({
        id: 'f1',
        status: 'Not Satisfied',
        recommendation_id: 'REC012',
        dimension: 'Question Clarity',
      }),
      finding({
        id: 'f2',
        status: 'Not Satisfied',
        recommendation_id: 'REC012',
        requirement_id: 'REQ011',
        dimension: 'Question Clarity',
      }),
      finding({
        id: 'f3',
        status: 'Not Satisfied',
        recommendation_id: 'REC018',
        requirement_id: 'REQ018',
        dimension: 'Marks and Totals',
      }),
      finding({
        id: 'f4',
        status: 'Satisfied',
        recommendation_id: 'REC030',
        requirement_id: 'REQ030',
        dimension: 'Marks and Totals',
      }),
    ])

    expect(groups.map((group) => group.section)).toEqual(['questions', 'marks-structure'])
    expect(groups[0].findings.map((item) => item.id)).toEqual(['f1'])
    expect(groups[1].findings.map((item) => item.id)).toEqual(['f3'])
  })
})

describe('statusDistributionCounts', () => {
  it('reads the five authoritative counts directly from the score response', () => {
    const score: AnalysisScoreResponse = {
      analysis_id: 'analysis-1',
      score: '80.00',
      label: null,
      denominator: 5,
      satisfied_count: 3,
      partially_satisfied_count: 1,
      not_satisfied_count: 1,
      not_verified_count: 2,
      not_applicable_count: 0,
    }
    expect(statusDistributionCounts(score)).toEqual({
      Satisfied: 3,
      'Partially Satisfied': 1,
      'Not Satisfied': 1,
      'Not Verified': 2,
      'Not Applicable': 0,
    })
  })
})
