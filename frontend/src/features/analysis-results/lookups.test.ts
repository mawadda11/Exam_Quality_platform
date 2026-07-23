import { describe, expect, it } from 'vitest'
import type { CloResponse, QuestionResponse, TopicResponse } from '../../types/api'
import { buildLookups } from './lookups'

function clo(code: string, text: string): CloResponse {
  return {
    id: `clo-${code}`,
    analysis_id: 'analysis-1',
    code,
    text,
    program_outcome_reference: null,
    page_number: 1,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  }
}

function topic(code: string | null, text: string): TopicResponse {
  return {
    id: `topic-${code ?? 'none'}`,
    analysis_id: 'analysis-1',
    code,
    text,
    expected_hours: null,
    page_number: 1,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  }
}

function question(numberLabel: string, text: string): QuestionResponse {
  return {
    id: `q-${numberLabel}`,
    analysis_id: 'analysis-1',
    parent_question_id: null,
    number_label: numberLabel,
    question_text: text,
    page_number: 1,
    marks: 5,
    sequence: 1,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  }
}

describe('buildLookups', () => {
  it('indexes CLOs, topics, and questions by their citable code/label', () => {
    const lookups = buildLookups(
      [clo('CLO1', 'Explain core concepts')],
      [topic('T1', 'Data structures')],
      [question('Q1', 'Explain a stack.')],
    )

    expect(lookups.cloByCode.get('CLO1')?.text).toBe('Explain core concepts')
    expect(lookups.topicByCode.get('T1')?.text).toBe('Data structures')
    expect(lookups.questionByLabel.get('Q1')?.question_text).toBe('Explain a stack.')
  })

  it('excludes topics with no code, since they cannot be cited deterministically', () => {
    const lookups = buildLookups([], [topic(null, 'Uncoded topic')], [])
    expect(lookups.topicByCode.size).toBe(0)
  })
})
