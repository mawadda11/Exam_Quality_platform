import { describe, expect, it } from 'vitest'
import type { ExtractionReviewSnapshot } from '../../types/api'
import {
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
})
