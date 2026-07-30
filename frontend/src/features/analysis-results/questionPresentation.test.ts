import { describe, expect, it } from 'vitest'
import type { FindingResponse, QuestionResponse } from '../../types/api'
import {
  buildQuestionRows,
  EMPTY_QUESTION_FILTERS,
  filterQuestionRows,
} from './questionPresentation'

function question(overrides: Partial<QuestionResponse> = {}): QuestionResponse {
  return {
    id: 'question-1',
    analysis_id: 'analysis-1',
    parent_question_id: null,
    number_label: 'Q1',
    question_text: 'Which operation has O(1) time complexity?',
    page_number: 1,
    marks: 5,
    sequence: 1,
    confidence: 0.9,
    geometry: null,
    created_at: '2026-07-26T00:00:00Z',
    ...overrides,
  }
}

function finding(overrides: Partial<FindingResponse> = {}): FindingResponse {
  return {
    id: 'finding-1',
    analysis_id: 'analysis-1',
    requirement_id: 'REQ011',
    rule_id: 'RULE011',
    recommendation_id: null,
    status: 'Satisfied',
    explanation: 'Clear and unambiguous.',
    confidence: 0.95,
    confidence_level: null,
    evaluation_details: null,
    evaluator_type: 'deterministic_rule',
    ai_provider: null,
    ai_model: null,
    prompt_template_version: null,
    kb_version: null,
    created_at: '2026-07-26T00:00:00Z',
    evidence: [],
    requirement_name: 'Question Clarity',
    dimension: 'Question Clarity',
    source_type: 'Exam',
    officiality: 'System Rule',
    ...overrides,
  }
}

describe('buildQuestionRows', () => {
  it('derives the worst related status per question without inventing new statuses', () => {
    const q1 = question({ id: 'q1', number_label: 'Q1' })
    const clarityFinding = finding({
      id: 'f1',
      status: 'Satisfied',
      evidence: [
        {
          id: 'e1',
          source_document: 'exam',
          evidence_type: 'question_text',
          page_number: 1,
          item_reference: 'Q1',
        },
      ],
    })
    const marksFinding = finding({
      id: 'f2',
      rule_id: 'RULE018',
      status: 'Not Satisfied',
      dimension: 'Marks and Totals',
      evidence: [
        {
          id: 'e2',
          source_document: 'exam',
          evidence_type: 'marks',
          page_number: 1,
          item_reference: 'Q1',
        },
      ],
    })

    const rows = buildQuestionRows([q1], [clarityFinding, marksFinding])

    expect(rows).toHaveLength(1)
    expect(rows[0].status).toBe('Not Satisfied')
    expect(rows[0].findings.map((item) => item.id)).toEqual(['f1', 'f2'])
  })

  it('leaves status null when no finding cites the question', () => {
    const rows = buildQuestionRows([question()], [])
    expect(rows[0].status).toBeNull()
    expect(rows[0].findings).toHaveLength(0)
  })

  it('collects CLO and topic references from item judgments that cite the question', () => {
    const q1 = question({ id: 'q1', number_label: 'Q1' })
    const alignment = finding({
      id: 'f3',
      rule_id: 'RULE001',
      status: 'Satisfied',
      dimension: 'CLO Alignment',
      evidence: [
        {
          id: 'src',
          source_document: 'exam',
          evidence_type: 'question_text',
          page_number: 1,
          item_reference: 'Q1',
        },
        {
          id: 'tgt',
          source_document: 'tp153',
          evidence_type: 'clo',
          page_number: 2,
          item_reference: 'CLO1',
        },
      ],
      evaluation_details: {
        schema_version: 1,
        decision: 'Satisfied',
        evidence_used: ['src', 'tgt'],
        reasoning: 'Matches.',
        recommendation: null,
        confidence_basis: [],
        item_judgments: [
          {
            source_evidence_id: 'src',
            target_evidence_ids: ['tgt'],
            status: 'Satisfied',
            reasoning: 'Matches.',
          },
        ],
        retrieved_knowledge_ids: [],
      },
    })

    const rows = buildQuestionRows([q1], [alignment])

    expect(rows[0].cloReferences).toEqual(['CLO1'])
    expect(rows[0].topicReferences).toEqual([])
  })

  it('scopes evidence to the question itself, excluding other questions and exam-wide totals cited by a shared finding', () => {
    const q1b = question({ id: 'q1b', number_label: 'Q1(b)' })
    // An analysis-wide "Correct Total Marks" style finding whose evidence array
    // spans every question in the exam plus the declared/calculated totals.
    const totalsFinding = finding({
      id: 'f-rule018',
      rule_id: 'RULE018',
      status: 'Satisfied',
      dimension: 'Marks and Totals',
      evidence: [
        {
          id: 'e-q1b-marks',
          source_document: 'exam',
          evidence_type: 'marks',
          page_number: 1,
          item_reference: 'Q1(b)',
        },
        {
          id: 'e-q2-marks',
          source_document: 'exam',
          evidence_type: 'marks',
          page_number: 2,
          item_reference: 'Q2',
        },
        {
          id: 'e-q3-marks',
          source_document: 'exam',
          evidence_type: 'marks',
          page_number: 3,
          item_reference: 'Q3',
        },
        {
          id: 'e-declared-total',
          source_document: 'exam',
          evidence_type: 'exam_metadata',
          page_number: 1,
          item_reference: 'declared_total',
        },
        {
          id: 'e-calculated-total',
          source_document: 'exam',
          evidence_type: 'exam_metadata',
          page_number: 1,
          item_reference: 'calculated_total',
        },
      ],
    })
    // A CLO alignment finding whose judgment, sourced from Q1(b), links to CLO1.
    const alignment = finding({
      id: 'f-rule001',
      rule_id: 'RULE001',
      status: 'Satisfied',
      dimension: 'CLO Alignment',
      evidence: [
        {
          id: 'e-q1b-text',
          source_document: 'exam',
          evidence_type: 'question_text',
          page_number: 1,
          item_reference: 'Q1(b)',
        },
        {
          id: 'e-clo1',
          source_document: 'tp153',
          evidence_type: 'clo',
          page_number: 2,
          item_reference: 'CLO1',
        },
      ],
      evaluation_details: {
        schema_version: 1,
        decision: 'Satisfied',
        evidence_used: ['e-q1b-text', 'e-clo1'],
        reasoning: 'Matches.',
        recommendation: null,
        confidence_basis: [],
        item_judgments: [
          {
            source_evidence_id: 'e-q1b-text',
            target_evidence_ids: ['e-clo1'],
            status: 'Satisfied',
            reasoning: 'Matches.',
          },
        ],
        retrieved_knowledge_ids: [],
      },
    })

    const rows = buildQuestionRows([q1b], [totalsFinding, alignment])
    const evidenceIds = rows[0].evidence.map((item) => item.id)

    expect(evidenceIds).toEqual(
      expect.arrayContaining(['e-q1b-marks', 'e-q1b-text', 'e-clo1']),
    )
    expect(evidenceIds).not.toContain('e-q2-marks')
    expect(evidenceIds).not.toContain('e-q3-marks')
    expect(evidenceIds).not.toContain('e-declared-total')
    expect(evidenceIds).not.toContain('e-calculated-total')
    expect(rows[0].evidence).toHaveLength(3)
  })
})

describe('filterQuestionRows', () => {
  const rows = buildQuestionRows(
    [
      question({ id: 'q1', number_label: 'Q1', question_text: 'Linked list operations' }),
      question({ id: 'q2', number_label: 'Q2', question_text: 'Binary search trees' }),
    ],
    [
      finding({
        id: 'f1',
        status: 'Not Verified',
        evidence: [
          {
            id: 'e1',
            source_document: 'exam',
            evidence_type: 'question_text',
            page_number: 1,
            item_reference: 'Q2',
          },
        ],
      }),
    ],
  )

  it('matches search text against the question identifier', () => {
    const filtered = filterQuestionRows(rows, { ...EMPTY_QUESTION_FILTERS, search: 'q1' })
    expect(filtered.map((row) => row.question.number_label)).toEqual(['Q1'])
  })

  it('matches search text against the question text', () => {
    const filtered = filterQuestionRows(rows, {
      ...EMPTY_QUESTION_FILTERS,
      search: 'binary search',
    })
    expect(filtered.map((row) => row.question.number_label)).toEqual(['Q2'])
  })

  it('filters by status', () => {
    const filtered = filterQuestionRows(rows, {
      ...EMPTY_QUESTION_FILTERS,
      status: 'Not Verified',
    })
    expect(filtered.map((row) => row.question.number_label)).toEqual(['Q2'])
  })

  it('returns no rows when nothing matches', () => {
    const filtered = filterQuestionRows(rows, { ...EMPTY_QUESTION_FILTERS, search: 'graphs' })
    expect(filtered).toHaveLength(0)
  })
})
