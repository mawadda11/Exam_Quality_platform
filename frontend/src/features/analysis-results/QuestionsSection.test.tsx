import { fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { I18nProvider } from '../../i18n/I18nProvider'
import type { CloResponse, FindingResponse, QuestionResponse, TopicResponse } from '../../types/api'
import { QuestionsSection } from './QuestionsSection'

const PARENT: QuestionResponse = {
  id: 'parent-1',
  analysis_id: 'analysis-1',
  parent_question_id: null,
  number_label: 'Q1',
  question_text: 'Answer both parts.',
  page_number: 1,
  marks: 10,
  sequence: 1,
  confidence: 0.95,
  geometry: null,
  created_at: '2026-07-26T00:00:00Z',
}

const CHILD_A: QuestionResponse = {
  ...PARENT,
  id: 'child-a',
  parent_question_id: PARENT.id,
  number_label: 'Q1(a)',
  question_text: 'اكتب دالة hash table.',
  marks: 4,
  sequence: 2,
}

const CHILD_B: QuestionResponse = {
  ...PARENT,
  id: 'child-b',
  parent_question_id: PARENT.id,
  number_label: 'Q1(b)',
  question_text: 'Calculate x = 2 + 3.',
  marks: 6,
  sequence: 3,
}

const CLO1: CloResponse = {
  id: 'clo-1',
  analysis_id: 'analysis-1',
  code: 'CLO1',
  text: 'Explain fundamental computing concepts.',
  program_outcome_reference: null,
  page_number: 2,
  confidence: 0.9,
  geometry: null,
  created_at: '2026-07-26T00:00:00Z',
}

const TOPIC1: TopicResponse = {
  id: 'topic-1',
  analysis_id: 'analysis-1',
  code: 'TOPIC1',
  text: 'Data structures',
  expected_hours: null,
  page_number: 2,
  confidence: 0.9,
  geometry: null,
  created_at: '2026-07-26T00:00:00Z',
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

const CHILD_A_FINDING = finding({
  id: 'finding-a',
  status: 'Not Verified',
  evidence: [
    {
      id: 'evidence-a',
      source_document: 'exam',
      evidence_type: 'question_text',
      page_number: 1,
      item_reference: 'Q1(a)',
    },
  ],
})

const CHILD_A_CLO_FINDING = finding({
  id: 'finding-clo',
  requirement_id: 'REQ001',
  rule_id: 'RULE001',
  dimension: 'CLO Alignment',
  evidence: [
    {
      id: 'src-a',
      source_document: 'exam',
      evidence_type: 'question_text',
      page_number: 1,
      item_reference: 'Q1(a)',
    },
    {
      id: 'target-clo',
      source_document: 'tp153',
      evidence_type: 'clo',
      page_number: 2,
      item_reference: 'CLO1',
    },
  ],
  evaluation_details: {
    schema_version: 1,
    decision: 'Satisfied',
    evidence_used: ['src-a', 'target-clo'],
    reasoning: 'Matches.',
    recommendation: null,
    confidence_basis: [],
    item_judgments: [
      {
        source_evidence_id: 'src-a',
        target_evidence_ids: ['target-clo'],
        status: 'Satisfied',
        reasoning: 'Matches.',
      },
    ],
    retrieved_knowledge_ids: [],
  },
})

const CHILD_B_TOPIC_FINDING = finding({
  id: 'finding-topic',
  requirement_id: 'REQ007',
  rule_id: 'RULE007',
  dimension: 'Topic Alignment',
  evidence: [
    {
      id: 'src-b',
      source_document: 'exam',
      evidence_type: 'question_text',
      page_number: 1,
      item_reference: 'Q1(b)',
    },
    {
      id: 'target-topic',
      source_document: 'tp153',
      evidence_type: 'topic',
      page_number: 2,
      item_reference: 'TOPIC1',
    },
  ],
  evaluation_details: {
    schema_version: 1,
    decision: 'Satisfied',
    evidence_used: ['src-b', 'target-topic'],
    reasoning: 'Matches.',
    recommendation: null,
    confidence_basis: [],
    item_judgments: [
      {
        source_evidence_id: 'src-b',
        target_evidence_ids: ['target-topic'],
        status: 'Satisfied',
        reasoning: 'Matches.',
      },
    ],
    retrieved_knowledge_ids: [],
  },
})

function renderSection(props: Partial<Parameters<typeof QuestionsSection>[0]> = {}) {
  return render(
    <I18nProvider>
      <QuestionsSection
        questions={[PARENT, CHILD_A, CHILD_B]}
        findings={{
          status: 'ready',
          data: [CHILD_A_FINDING, CHILD_A_CLO_FINDING, CHILD_B_TOPIC_FINDING],
        }}
        {...props}
      />
    </I18nProvider>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
  window.localStorage.setItem('exam-quality-analyzer-locale', 'en')
})

describe('QuestionsSection', () => {
  it('keeps the compact legacy four-column table and omits structural parents', () => {
    renderSection()

    const table = screen.getByRole('table', { name: 'Extracted questions' })
    expect(within(table).getAllByRole('columnheader').map((header) => header.textContent)).toEqual([
      'Question',
      'Page',
      'Marks',
      'Text',
    ])
    expect(within(table).queryByText('Q1')).not.toBeInTheDocument()
    expect(within(table).getByText('Q1(a)').closest('bdi')).toBeInTheDocument()
    expect(within(table).getByText('Q1(b)').closest('bdi')).toBeInTheDocument()
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(screen.queryByRole('button', { name: /view details/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/Evidence \(148\)/i)).not.toBeInTheDocument()
  })

  it('filters by question identifier and question text', () => {
    renderSection()
    fireEvent.change(screen.getByLabelText('Search questions'), { target: { value: 'Q1(b)' } })
    expect(screen.queryByText('Q1(a)')).not.toBeInTheDocument()
    expect(screen.getByText('Q1(b)')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Search questions'), {
      target: { value: 'hash table' },
    })
    expect(screen.getByText('Q1(a)')).toBeInTheDocument()
    expect(screen.queryByText('Q1(b)')).not.toBeInTheDocument()
  })

  it('shows only the search control and removes unused academic filters', () => {
    renderSection()

    expect(screen.getByLabelText('Search questions')).toBeInTheDocument()
    expect(screen.queryByLabelText('Status')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('CLO')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Course topic')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Clear filters' })).not.toBeInTheDocument()
  })

  it('shows distinct extraction and no-match empty states', () => {
    const { rerender } = renderSection()
    fireEvent.change(screen.getByLabelText('Search questions'), {
      target: { value: 'nonexistent-question' },
    })
    expect(screen.getByText('No questions match the filters.')).toBeInTheDocument()
    expect(screen.getByText('Clear the filters to see every extracted question.')).toBeInTheDocument()

    rerender(
      <I18nProvider>
        <QuestionsSection questions={[]} />
      </I18nProvider>,
    )
    expect(screen.getByText('No questions were extracted for this analysis.')).toBeInTheDocument()
  })

  it('preserves original Arabic question text and automatic text direction', () => {
    renderSection()
    expect(screen.getByText(CHILD_A.question_text)).toHaveAttribute('dir', 'auto')
  })
})
