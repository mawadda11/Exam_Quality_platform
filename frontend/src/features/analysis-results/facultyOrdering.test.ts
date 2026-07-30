import { describe, expect, it } from 'vitest'
import type { QuestionResponse } from '../../types/api'
import {
  compareNaturalCloIdentifiers,
  compareNaturalQuestionReferences,
  independentlyScorableQuestions,
  sortQuestionReferences,
  sortQuestionsForFaculty,
} from './facultyOrdering'

function question(
  id: string,
  numberLabel: string,
  overrides: Partial<QuestionResponse> = {},
): QuestionResponse {
  return {
    id,
    analysis_id: 'analysis-1',
    parent_question_id: null,
    number_label: numberLabel,
    question_text: `${numberLabel} text`,
    page_number: 1,
    marks: 1,
    sequence: 0,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('faculty natural ordering', () => {
  it('orders Western and Arabic-Indic question references naturally', () => {
    expect(['Q10', 'Q3', 'Q1', 'Q2'].sort(compareNaturalQuestionReferences))
      .toEqual(['Q1', 'Q2', 'Q3', 'Q10'])
    expect(['س١٠', 'س٢', 'س١'].sort(compareNaturalQuestionReferences))
      .toEqual(['س١', 'س٢', 'س١٠'])
  })

  it('places parents before numeric, Latin, and Arabic child references', () => {
    expect(
      ['Q2.2', 'Q3', 'Q2', 'Q2.1', 'Q2(b)', 'Q2(a)']
        .sort(compareNaturalQuestionReferences),
    ).toEqual(['Q2', 'Q2.1', 'Q2.2', 'Q2(a)', 'Q2(b)', 'Q3'])
    expect(['٣', '٢-ب', '٢', '٢-أ'].sort(compareNaturalQuestionReferences))
      .toEqual(['٢', '٢-أ', '٢-ب', '٣'])
  })

  it('prefers confirmed sequence and enforces parent-before-child hierarchy', () => {
    const parent = question('parent', 'Q2', { sequence: 2 })
    const child = question('child', 'Q2.1', {
      parent_question_id: 'parent',
      sequence: 1,
    })
    const first = question('first', 'Q1', { sequence: 1 })

    expect(sortQuestionsForFaculty([child, parent, first]).map((item) => item.id))
      .toEqual(['first', 'parent', 'child'])
  })

  it('returns only the lowest independently scorable question level', () => {
    const parent = question('parent', 'Q1', { marks: 10 })
    const childA = question('child-a', 'Q1(a)', {
      parent_question_id: parent.id,
      marks: 4,
    })
    const childB = question('child-b', 'Q1(b)', {
      parent_question_id: parent.id,
      marks: 6,
    })
    const standalone = question('standalone', 'Q2', { marks: 5 })

    expect(
      independentlyScorableQuestions([parent, childA, childB, standalone]).map(
        (item) => item.id,
      ),
    ).toEqual(['child-a', 'child-b', 'standalone'])
  })

  it('falls back to page, natural reference, and stable identifier order', () => {
    const references = ['missing-b', 'Q10', 'Q2', 'missing-a']
    const pages = new Map([
      ['Q10', 1],
      ['Q2', 1],
      ['missing-b', 4],
      ['missing-a', 4],
    ])
    expect(sortQuestionReferences(references, [], pages))
      .toEqual(['Q2', 'Q10', 'missing-a', 'missing-b'])

    expect(
      sortQuestionsForFaculty([
        question('stable-b', '', { page_number: 5 }),
        question('stable-a', '', { page_number: 5 }),
      ]).map((item) => item.id),
    ).toEqual(['stable-a', 'stable-b'])
  })

  it('orders CLO identifiers naturally when official order is unavailable', () => {
    expect(['CLO10', 'CLO3', 'CLO1', 'CLO2'].sort(compareNaturalCloIdentifiers))
      .toEqual(['CLO1', 'CLO2', 'CLO3', 'CLO10'])
  })
})
