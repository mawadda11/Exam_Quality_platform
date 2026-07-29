import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../i18n/I18nProvider'
import type {
  AnalysisResponse,
  AssessmentRecordResponse,
  CloResponse,
  FindingResponse,
  QuestionResponse,
  TopicResponse,
} from '../../types/api'
import { AlignmentCoverageSection } from './AlignmentCoverageSection'
import type { ResultResource } from './useAnalysisResultsData'

function ready<T>(data: T): ResultResource<T> {
  return { status: 'ready', data }
}

const ANALYSIS: AnalysisResponse = {
  id: 'analysis-1',
  course: {
    id: 'course-1',
    code: 'CPIT-450',
    name: 'Software Engineering',
    department: null,
    program: null,
  },
  exam_type: 'Midterm',
  term: '2026 Spring',
  state: 'completed',
  owner_user_id: 'user-1',
  predecessor_analysis_id: null,
  uploaded_files: [],
  exam_uploaded: true,
  tp153_uploaded: true,
  ready_for_analysis: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function finding(overrides: Partial<FindingResponse>): FindingResponse {
  return {
    id: 'finding-1',
    analysis_id: 'analysis-1',
    requirement_id: 'REQ001',
    rule_id: 'RULE001',
    recommendation_id: null,
    status: 'Satisfied',
    explanation: 'The available evidence supports this academic result.',
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
    requirement_name: 'Question-to-CLO Mapping',
    dimension: 'CLO Alignment',
    source_type: 'Derived Exam Requirement',
    officiality: 'Derived',
    ...overrides,
  }
}

const QUESTIONS: QuestionResponse[] = [
  {
    id: 'q-10',
    analysis_id: 'analysis-1',
    parent_question_id: null,
    number_label: 'Q10',
    question_text: 'Explain transaction recovery.',
    page_number: 4,
    marks: 5,
    sequence: 10,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'q-1',
    analysis_id: 'analysis-1',
    parent_question_id: null,
    number_label: 'Q1',
    question_text: 'Define a database.',
    page_number: 1,
    marks: 5,
    sequence: 1,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'q-2',
    analysis_id: 'analysis-1',
    parent_question_id: null,
    number_label: 'Q2',
    question_text: 'Design a relational database schema.',
    page_number: 2,
    marks: 10,
    sequence: 2,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
]

const CLOS: CloResponse[] = [
  {
    id: 'clo-2',
    analysis_id: 'analysis-1',
    code: 'CLO2',
    text: 'Design relational database solutions.',
    program_outcome_reference: null,
    page_number: 1,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'clo-10',
    analysis_id: 'analysis-1',
    code: 'CLO10',
    text: 'Evaluate advanced data systems.',
    program_outcome_reference: null,
    page_number: 2,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
]

const TOPICS: TopicResponse[] = [
  {
    id: 'topic-database',
    analysis_id: 'analysis-1',
    code: null,
    text: 'Database design',
    expected_hours: 6,
    page_number: 3,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'topic-network',
    analysis_id: 'analysis-1',
    code: null,
    text: 'Computer networks',
    expected_hours: 6,
    page_number: 4,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
]

const ASSESSMENTS: AssessmentRecordResponse[] = [
  {
    id: 'assessment-final',
    analysis_id: 'analysis-1',
    method: 'Written examination',
    activity: 'Final',
    percentage: 50,
    page_number: 4,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'assessment-midterm',
    analysis_id: 'analysis-1',
    method: 'Written examination',
    activity: 'Midterm',
    percentage: 30,
    page_number: 4,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
]

function relationshipFinding(type: 'clo' | 'topic'): FindingResponse {
  const targetReference = type === 'clo' ? 'CLO2' : 'Database design'
  const targetId = `${type}-target`
  const ruleId = type === 'clo' ? 'RULE001' : 'RULE007'
  return finding({
    id: `${type}-relationship`,
    rule_id: ruleId,
    dimension: type === 'clo' ? 'CLO Alignment' : 'Topic Alignment',
    requirement_name:
      type === 'clo'
        ? 'Question-to-CLO Mapping'
        : 'Question-to-topic alignment',
    status: type === 'clo' ? 'Partially Satisfied' : 'Satisfied',
    evidence: [
      {
        id: `${type}-q2`,
        source_document: 'exam',
        evidence_type: 'question_text',
        page_number: 2,
        item_reference: 'Q2',
      },
      {
        id: `${type}-q10`,
        source_document: 'exam',
        evidence_type: 'question_text',
        page_number: 4,
        item_reference: 'Q10',
      },
      {
        id: targetId,
        source_document: 'tp153',
        evidence_type: type,
        page_number: type === 'clo' ? 1 : 3,
        item_reference: targetReference,
      },
    ],
    evaluation_details: {
      schema_version: 1,
      decision: type === 'clo' ? 'Partially Satisfied' : 'Satisfied',
      evidence_used: [`${type}-q2`, `${type}-q10`, targetId],
      reasoning: 'The linked items share assessed content.',
      recommendation: null,
      confidence_basis: ['The linked excerpts were readable.'],
      item_judgments: [
        {
          source_evidence_id: `${type}-q2`,
          target_evidence_ids: [targetId],
          status: type === 'clo' ? 'Partially Satisfied' : 'Satisfied',
          reasoning:
            type === 'clo'
              ? 'One normalized assessed concept is shared; the local evidence is limited.'
              : 'The question directly assesses database design.',
        },
        {
          source_evidence_id: `${type}-q10`,
          target_evidence_ids: [targetId],
          status: 'Not Satisfied',
          reasoning: 'No supported relationship was found.',
        },
      ],
      retrieved_knowledge_ids: ['REQ001', ruleId],
    },
  })
}

function renderSection(
  overrides: Partial<React.ComponentProps<typeof AlignmentCoverageSection>> = {},
  translated = false,
) {
  const onRetry = vi.fn()
  const tree = (
    <MemoryRouter>
      <AlignmentCoverageSection
        analysis={ANALYSIS}
        findings={ready([
          relationshipFinding('clo'),
          relationshipFinding('topic'),
          finding({
            id: 'clo-coverage',
            rule_id: 'RULE005',
            dimension: 'CLO Coverage',
            requirement_name: 'Applicable CLO Coverage',
          }),
          finding({
            id: 'topic-coverage',
            rule_id: 'RULE009',
            dimension: 'Topic Coverage',
            requirement_name: 'Applicable topic coverage',
          }),
          finding({
            id: 'assessment',
            rule_id: 'RULE003',
            dimension: 'Assessment Alignment',
            requirement_name: 'Assessment Method Consistency',
          }),
        ])}
        questions={ready(QUESTIONS)}
        clos={ready(CLOS)}
        topics={ready(TOPICS)}
        assessmentRecords={ready(ASSESSMENTS)}
        onRetry={onRetry}
        {...overrides}
      />
    </MemoryRouter>
  )
  const result = render(translated ? <I18nProvider>{tree}</I18nProvider> : tree)
  return { ...result, onRetry }
}

beforeEach(() => {
  window.localStorage.clear()
})

describe('AlignmentCoverageSection', () => {
  it('renders exactly one combined relationship table and two coverage tables', () => {
    renderSection()

    expect(screen.getAllByRole('table')).toHaveLength(3)
    expect(
      screen.getByRole('table', {
        name: 'Question-to-CLO-and-Topic relationships',
      }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('table', { name: 'Question-to-CLO relationships' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('table', { name: 'Question-to-topic relationships' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'CLO Coverage' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Topic Coverage' })).toBeInTheDocument()
    expect(screen.getAllByText('Assessment Method Consistency').length)
      .toBeGreaterThan(0)
  })

  it('uses natural question order, preserves official CLO/topic order, and aligns related lists', () => {
    renderSection()

    const relationshipTable = screen.getByRole('table', {
      name: 'Question-to-CLO-and-Topic relationships',
    })
    expect(
      within(relationshipTable)
        .getAllByRole('rowheader')
        .map((header) => header.textContent),
    ).toEqual(['Q1', 'Q2', 'Q10'])

    const cloTable = screen.getByRole('table', { name: 'CLO Coverage' })
    expect(
      within(cloTable).getAllByRole('rowheader').map((header) => header.textContent),
    ).toEqual(['CLO2', 'CLO10'])
    expect(within(cloTable).getByText('Q2').closest('td')).toHaveTextContent(
      'Q2, Q10',
    )

    const topicTable = screen.getByRole('table', { name: 'Topic Coverage' })
    expect(
      within(topicTable)
        .getAllByRole('rowheader')
        .map((header) => header.textContent),
    ).toEqual(['Database design', 'Computer networks'])
    expect(within(topicTable).getByText('Q2').closest('td')).toHaveTextContent(
      'Q2, Q10',
    )
  })

  it('keeps differing CLO/topic judgments separate and opens a compact selected-question comparison', () => {
    const { container } = renderSection()
    const relationshipTable = screen.getByRole('table', {
      name: 'Question-to-CLO-and-Topic relationships',
    })
    const q2Row = within(relationshipTable)
      .getByRole('rowheader', { name: 'Q2' })
      .closest('tr')!

    const states = q2Row.querySelector<HTMLElement>(
      '.relationship-status-list',
    )!
    expect(within(states).getByText('CLO:', { exact: false }).parentElement)
      .toHaveTextContent('CLO: Partially supported')
    expect(within(states).getByText('Course Topic:', { exact: false }).parentElement)
      .toHaveTextContent('Course Topic: Supported')
    expect(
      within(q2Row).getByText(
        'The question shares a relevant concept with the suggested item, but the relationship is limited.',
      ),
    ).toBeInTheDocument()

    fireEvent.click(
      within(q2Row).getByRole('button', { name: 'View comparison' }),
    )
    const comparison = container.querySelector<HTMLElement>(
      '#question-comparison',
    )!
    expect(comparison).toHaveAttribute('open')
    expect(within(comparison).getByText('Design a relational database schema.'))
      .toHaveAttribute('dir', 'auto')
    expect(within(comparison).getByText('Design relational database solutions.'))
      .toHaveAttribute('dir', 'auto')
    expect(within(comparison).getByText('Database design')).toHaveAttribute(
      'dir',
      'auto',
    )
    expect(comparison).toHaveTextContent('Q2 — Exam, page 2')
    expect(comparison).toHaveTextContent('CLO2 — Course Specification, page 1')
    expect(comparison).toHaveTextContent(
      'Course Topic — Course Specification, page 3',
    )
    expect(comparison).not.toHaveTextContent('Original document excerpt')
    expect(comparison).not.toHaveTextContent('EVIDENCE TYPE')
  })

  it('shows one compact assessment result and only its matching method', () => {
    const { container } = renderSection()
    const section = container.querySelector<HTMLElement>(
      '#assessment-method-consistency',
    )!

    expect(section).toHaveTextContent('Satisfied')
    expect(section).toHaveTextContent(
      'The document was identified as a Midterm Examination, and a matching assessment method was found in the Course Specification.',
    )
    fireEvent.click(within(section).getByText('View comparison'))
    expect(section).toHaveTextContent('Written examination — Midterm')
    expect(section).not.toHaveTextContent('Written examination — Final')
    expect(screen.queryByText(/Assessment-method evidence/)).not.toBeInTheDocument()
  })

  it('does not render raw academic evidence lists or repeated source metadata cards', () => {
    const { container } = renderSection()

    expect(screen.queryByText(/CLO alignment and coverage evidence/))
      .not.toBeInTheDocument()
    expect(screen.queryByText(/Topic alignment and coverage evidence/))
      .not.toBeInTheDocument()
    expect(screen.queryByText(/Assessment-method evidence/))
      .not.toBeInTheDocument()
    expect(screen.queryByText('Official Course Specification records'))
      .not.toBeInTheDocument()
    expect(container.querySelector('.evidence-item')).not.toBeInTheDocument()
    expect(screen.queryByText('SOURCE')).not.toBeInTheDocument()
    expect(screen.queryByText('PAGE')).not.toBeInTheDocument()
    expect(screen.queryByText('REFERENCE')).not.toBeInTheDocument()
  })

  it('uses the approved Arabic terminology and RTL presentation', () => {
    window.localStorage.setItem('exam-quality-analyzer-locale', 'ar')
    renderSection({}, true)

    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    expect(
      screen.getByRole('columnheader', { name: 'ناتج التعلم المقترح' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('columnheader', { name: 'موضوع المقرر المقترح' }),
    ).toBeInTheDocument()
    expect(screen.getAllByText('عرض المقارنة').length).toBeGreaterThan(0)
    expect(screen.getAllByText('لم يظهر ارتباط واضح').length)
      .toBeGreaterThan(0)
  })

  it('keeps successful sections available and retries a failed source resource', () => {
    const { onRetry } = renderSection({
      assessmentRecords: {
        status: 'error',
        message: 'Assessment records unavailable.',
      },
    })

    expect(screen.getAllByText('CLO2').length).toBeGreaterThan(0)
    expect(screen.getByText(/assessment records unavailable/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledWith('assessmentRecords')
  })
})
