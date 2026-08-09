import { describe, expect, it } from 'vitest'
import type { ExtractionReviewSnapshot } from '../../types/api'
import {
  applyPastedQuestionRows,
  applyStructuredQuestionRows,
  parsePastedQuestions,
  parseStructuredQuestionTemplate,
  StructuredQuestionTemplateError,
} from './structuredQuestionTemplate'

function emptySnapshot(): ExtractionReviewSnapshot {
  return {
    schema_version: 2,
    preparation_mode: 'structured_template',
    questions: [],
    question_options: [],
    question_blanks: [],
    question_source_spans: [],
    extraction_warnings: [],
    evidence: [],
    clos: [],
    topics: [],
    assessment_records: [],
    supporting_materials: [],
    supporting_annotations: [],
    document_references: [],
    reference_associations: [],
  }
}

const SIMPLE_HEADER = 'question_number,question_text,marks,question_type,options'
const LEGACY_HEADER =
  'question_number,question_text,question_type,marks,page_number,parent_question_number,option_a,option_b,option_c,option_d'

describe('structured question template', () => {
  it('requires only question number, text, and marks columns', () => {
    const rows = parseStructuredQuestionTemplate(
      'question_number,question_text,marks\nQ1,"Explain why hash collisions are undesirable.",',
    )

    expect(rows).toHaveLength(1)
    expect(rows[0]).toMatchObject({
      questionNumber: 'Q1',
      questionText: 'Explain why hash collisions are undesirable.',
      marks: null,
      questionType: 'short_answer',
      pageNumber: 1,
    })
  })

  it('infers multiple choice from the compact options column', () => {
    const rows = parseStructuredQuestionTemplate(
      `${SIMPLE_HEADER}\nQ1,Which pattern constructs a complex object?,1,,Singleton|Builder|Prototype|Adapter`,
    )

    expect(rows[0]?.questionType).toBe('multiple_choice')
    expect(rows[0]?.options.map((option) => option.text)).toEqual([
      'Singleton',
      'Builder',
      'Prototype',
      'Adapter',
    ])
  })

  it('keeps missing marks empty instead of inventing a value', () => {
    const rows = parseStructuredQuestionTemplate(
      `${SIMPLE_HEADER}\nQ1,"Explain why hash collisions are undesirable.",,short_answer,`,
    )

    expect(rows[0]?.marks).toBeNull()
  })

  it('continues accepting the previous detailed CSV format', () => {
    const rows = parseStructuredQuestionTemplate(
      `${LEGACY_HEADER}\nQ1,"Which pattern constructs\na complex object step by step?",multiple_choice,1,2,,Singleton,Builder,Prototype,Adapter`,
    )

    expect(rows[0]?.pageNumber).toBe(2)
    expect(rows[0]?.questionText).toBe(
      'Which pattern constructs\na complex object step by step?',
    )
    expect(rows[0]?.options).toHaveLength(4)
  })

  it('rejects answer options for an explicitly non-multiple-choice question', () => {
    expect(() =>
      parseStructuredQuestionTemplate(
        `${SIMPLE_HEADER}\nQ1,Explain the pattern.,2,essay,Unexpected option|Another option`,
      ),
    ).toThrow(StructuredQuestionTemplateError)
  })

  it('parses pasted multiline questions, options, and explicit marks', () => {
    const rows = parsePastedQuestions(`
Q1. Which pattern constructs a complex object step by step? [1 mark]
A. Singleton
B. Builder
C. Prototype
D. Adapter

Q2. Explain why collisions are undesirable
in cryptographic hash functions. [2 marks]
`)

    expect(rows).toHaveLength(2)
    expect(rows[0]).toMatchObject({
      questionNumber: 'Q1',
      questionType: 'multiple_choice',
      marks: 1,
    })
    expect(rows[0]?.options).toHaveLength(4)
    expect(rows[1]?.questionText).toBe(
      'Explain why collisions are undesirable in cryptographic hash functions.',
    )
    expect(rows[1]?.marks).toBe(2)
  })

  it('does not treat technical parentheses as marks in pasted questions', () => {
    const rows = parsePastedQuestions('Q1. Perform the operation in GF (19) and explain it.')

    expect(rows[0]?.marks).toBeNull()
    expect(rows[0]?.questionText).toContain('GF (19)')
  })

  it('creates reviewed questions, traceable evidence, and options without PDF geometry', () => {
    const rows = parseStructuredQuestionTemplate(
      `${SIMPLE_HEADER}\nQ1,Which pattern constructs a complex object?,,multiple_choice,Singleton|Builder`,
    )
    let nextId = 0
    const result = applyStructuredQuestionRows(emptySnapshot(), rows, () => {
      nextId += 1
      return `00000000-0000-4000-8000-${String(nextId).padStart(12, '0')}`
    })

    expect(result.questions).toHaveLength(1)
    expect(result.questions[0]).toMatchObject({
      marks: null,
      geometry: null,
      extraction_method: 'structured_template',
      review_status: 'reviewed',
    })
    expect(result.evidence).toHaveLength(1)
    expect(result.question_options).toHaveLength(2)
  })
  it('replaces the visible assisted draft with pasted questions while preserving machine audit records', () => {
    const base = emptySnapshot()
    base.preparation_mode = 'assisted_pdf'
    base.questions = [{
      source_record_id: '00000000-0000-4000-8000-000000000101',
      included: true,
      parent_source_record_id: null,
      number_label: 'Q1',
      question_text: 'Machine draft text',
      page_number: 1,
      marks: 2,
      sequence: 1,
      extraction_confidence: 0.9,
      geometry: { x0: 1, top: 2, x1: 3, bottom: 4 },
      question_type: 'short_answer',
      instructions: null,
      extraction_method: 'pdfplumber',
      review_status: 'machine_extracted',
    }]
    base.evidence = [{
      source_record_id: '00000000-0000-4000-8000-000000000102',
      included: true,
      question_source_record_id: base.questions[0].source_record_id,
      source_document: 'exam',
      evidence_type: 'question_text',
      page_number: 1,
      item_reference: 'Q1',
      extracted_text: 'Machine draft text',
      extraction_confidence: 0.9,
      geometry: { x0: 1, top: 2, x1: 3, bottom: 4 },
    }]

    const rows = parsePastedQuestions('Q1. Correct pasted question text [3 marks]')
    let nextId = 200
    const result = applyPastedQuestionRows(base, rows, () => {
      nextId += 1
      return `00000000-0000-4000-8000-${String(nextId).padStart(12, '0')}`
    })

    expect(result.preparation_mode).toBe('assisted_pdf')
    expect(result.questions).toHaveLength(2)
    expect(result.questions[0]?.included).toBe(false)
    expect(result.questions[1]).toMatchObject({
      included: true,
      question_text: 'Correct pasted question text',
      marks: 3,
      geometry: null,
      extraction_method: 'pasted_review',
      review_status: 'reviewed',
    })
    expect(result.evidence[0]?.included).toBe(false)
    expect(result.evidence[1]?.geometry).toBeNull()
  })

})
