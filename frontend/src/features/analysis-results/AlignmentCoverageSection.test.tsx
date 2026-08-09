import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../i18n/I18nProvider'
import type {
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
          reasoning_ar:
            type === 'clo'
              ? 'يتناول السؤال مفهومًا مرتبطًا بناتج التعلم المقترح، لكن نطاق العلاقة محدود.'
              : 'يقيس السؤال تصميم قواعد البيانات بشكل مباشر.',
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
  it('renders two summary panels and three primary tables, with no collapsed coverage details', () => {
    const { container } = renderSection()

    expect(screen.getAllByRole('table')).toHaveLength(3)
    expect(
      screen.getByRole('table', {
        name: 'Question-to-CLO-and-Topic relationships',
      }),
    ).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'CLO Analysis' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Topic Analysis' })).toBeInTheDocument()
    expect(container.querySelectorAll('.alignment-compact-summary > li'))
      .toHaveLength(2)
    expect(screen.getByRole('heading', { name: 'Question Relationships' }))
      .toBeInTheDocument()
    expect(screen.getByText('Questions linked to a CLO')).toBeInTheDocument()
    expect(screen.getByText('Questions linked to a course topic'))
      .toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Coverage' })).toBeInTheDocument()
    expect(container.querySelector('#clo-coverage')).not.toBeNull()
    expect(container.querySelector('#clo-coverage details')).not.toBeInTheDocument()
    expect(container.querySelector('#topic-coverage details')).not.toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'CLO Analysis (2)' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Topic Analysis (2)' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('Assessment Method Consistency'))
      .not.toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Action' }))
      .not.toBeInTheDocument()
    expect(screen.getAllByRole('columnheader', { name: 'Details' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('columnheader', { name: 'Total marks' })).toHaveLength(2)
    expect(
      screen.getByText(
        'A Midterm or Final exam may legitimately cover a subset of course topics. Topic coverage is informational and does not by itself indicate a quality problem.',
      ),
    ).toBeInTheDocument()
  })

  it('uses only the five approved academic statuses everywhere, never unofficial renamed labels', () => {
    renderSection()

    expect(screen.queryByText('Supported')).not.toBeInTheDocument()
    expect(screen.queryByText('Partially supported')).not.toBeInTheDocument()
    expect(screen.queryByText('Not supported')).not.toBeInTheDocument()
    expect(screen.getAllByText('Satisfied').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Partially Satisfied').length).toBeGreaterThan(0)
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

    const cloTable = screen.getByRole('table', { name: 'CLO Analysis' })
    expect(
      within(cloTable).getAllByRole('rowheader').map((header) => header.textContent),
    ).toEqual(['CLO2', 'CLO10'])
    const cloLinkedCell = within(cloTable).getByText('Q2').closest('td')!
    expect(cloLinkedCell.querySelectorAll('.question-reference-chip')).toHaveLength(2)
    expect(cloLinkedCell).toHaveTextContent('Q2')
    expect(cloLinkedCell).toHaveTextContent('Q10')
    expect(cloLinkedCell).not.toHaveTextContent('Q2, Q10')

    const topicTable = screen.getByRole('table', { name: 'Topic Analysis' })
    expect(
      within(topicTable)
        .getAllByRole('rowheader')
        .map((header) => header.textContent),
    ).toEqual(['Database design', 'Computer networks'])
    const topicLinkedCell = within(topicTable).getByText('Q2').closest('td')!
    expect(topicLinkedCell.querySelectorAll('.question-reference-chip')).toHaveLength(2)
    expect(topicLinkedCell).toHaveTextContent('Q2')
    expect(topicLinkedCell).toHaveTextContent('Q10')
    expect(topicLinkedCell).not.toHaveTextContent('Q2, Q10')
  })

  it('shows total marks per CLO/topic from questions with a supported relationship only', () => {
    renderSection()

    const cloTable = screen.getByRole('table', { name: 'CLO Analysis' })
    const clo2Row = within(cloTable).getByRole('rowheader', { name: 'CLO2' }).closest('tr')!
    expect(clo2Row.querySelector('[data-label="Total marks"]')).toHaveTextContent('10')

    const topicTable = screen.getByRole('table', { name: 'Topic Analysis' })
    const databaseRow = within(topicTable)
      .getByRole('rowheader', { name: 'Database design' })
      .closest('tr')!
    expect(databaseRow.querySelector('[data-label="Total marks"]')).toHaveTextContent('10')
  })

  it('opens a CLO mapping-details drawer showing linked questions and returns focus on close', async () => {
    renderSection()
    const cloTable = screen.getByRole('table', { name: 'CLO Analysis' })
    const clo2Row = within(cloTable).getByRole('rowheader', { name: 'CLO2' }).closest('tr')!
    const trigger = within(clo2Row).getByRole('button', { name: 'View mapping details' })

    fireEvent.click(trigger)

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Design relational database solutions.')).toBeInTheDocument()
    expect(within(dialog).getAllByText('Q2').length).toBeGreaterThan(0)

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('omits the mapping-details action for a topic with no linked questions', () => {
    renderSection()
    const topicTable = screen.getByRole('table', { name: 'Topic Analysis' })
    const networksRow = within(topicTable)
      .getByRole('rowheader', { name: 'Computer networks' })
      .closest('tr')!

    expect(
      within(networksRow).queryByRole('button', { name: 'View mapping details' }),
    ).not.toBeInTheDocument()
    expect(networksRow.querySelector('[data-label="Details"]')).toHaveTextContent('—')
  })

  it('keeps differing CLO/topic judgments separate and opens a consistent mapping drawer', async () => {
    renderSection()
    const relationshipTable = screen.getByRole('table', {
      name: 'Question-to-CLO-and-Topic relationships',
    })
    const q2Row = within(relationshipTable)
      .getByRole('rowheader', { name: 'Q2' })
      .closest('tr')!

    const states = q2Row.querySelector<HTMLElement>('.relationship-status-list')!
    expect(within(states).getByText('CLO:', { exact: false }).parentElement)
      .toHaveTextContent('CLO: Partially Satisfied')
    expect(within(states).getByText('Course Topic:', { exact: false }).parentElement)
      .toHaveTextContent('Course Topic: Satisfied')

    const trigger = within(q2Row).getByRole('button', { name: 'View mapping details' })
    fireEvent.click(trigger)

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Design a relational database schema.'))
      .toHaveAttribute('dir', 'auto')
    expect(within(dialog).getByText('Design relational database solutions.'))
      .toHaveAttribute('dir', 'auto')
    expect(
      within(dialog).getByText('Database design', {
        selector: 'p[dir="auto"]',
      }),
    ).toHaveAttribute('dir', 'auto')
    expect(within(dialog).getByText('Suggested CLO')).toBeInTheDocument()
    expect(within(dialog).getByText('Suggested Course Topic')).toBeInTheDocument()
    expect(dialog).not.toHaveTextContent('Original document excerpt')
    expect(dialog).not.toHaveTextContent('EVIDENCE TYPE')

    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => expect(trigger).toHaveFocus())

    const badges = q2Row.querySelectorAll('.ui-status-badge')
    expect(badges).toHaveLength(2)
    expect(badges[0]).toHaveAttribute('data-academic-status', 'Partially Satisfied')
    expect(badges[1]).toHaveAttribute('data-academic-status', 'Satisfied')
    const q10Row = within(relationshipTable)
      .getByRole('rowheader', { name: 'Q10' })
      .closest('tr')!
    expect(within(q10Row).getAllByText('Not Satisfied')).toHaveLength(2)
    expect(
      q10Row.querySelectorAll('.ui-status-badge[data-academic-status="Not Satisfied"]'),
    ).toHaveLength(2)
  })

  it('does not duplicate the assessment-method result in Alignment', () => {
    renderSection()
    expect(screen.queryByText('Assessment Method Consistency'))
      .not.toBeInTheDocument()
    expect(screen.queryByText(/Written examination/)).not.toBeInTheDocument()
  })

  it('excludes structural parents from relationship rows and question counts', () => {
    const parent: QuestionResponse = {
      ...QUESTIONS[0],
      id: 'parent-q3',
      number_label: 'Q3',
      question_text: 'Answer all parts.',
      marks: 10,
      sequence: 3,
    }
    const child: QuestionResponse = {
      ...parent,
      id: 'child-q3-a',
      parent_question_id: parent.id,
      number_label: 'Q3(a)',
      question_text: 'Explain normalization.',
      marks: 4,
      sequence: 4,
    }
    renderSection({ questions: ready([parent, child]) })

    const relationshipTable = screen.getByRole('table', {
      name: 'Question-to-CLO-and-Topic relationships',
    })
    expect(within(relationshipTable).getByText('Q3(a)')).toBeInTheDocument()
    expect(within(relationshipTable).queryByText('Q3')).not.toBeInTheDocument()
    const relationshipsPanel = screen
      .getByRole('heading', { name: 'Question Relationships' })
      .closest('li')!
    expect(relationshipsPanel).toHaveTextContent('Questions linked to a CLO0')
    expect(relationshipsPanel).toHaveTextContent(
      'Questions linked to a course topic0',
    )
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
    expect(screen.getByRole('heading', { name: 'ربط الأسئلة' }))
      .toBeInTheDocument()
    expect(screen.getByText('أسئلة مرتبطة بمخرج تعلم')).toBeInTheDocument()
    expect(screen.getByText('أسئلة مرتبطة بموضوع مقرر')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'التغطية' })).toBeInTheDocument()
    expect(screen.getAllByText('عرض تفاصيل الربط').length).toBeGreaterThan(0)
    expect(screen.queryByText('عرض المقارنة')).not.toBeInTheDocument()
    expect(screen.getAllByText('لم يظهر ارتباط واضح').length)
      .toBeGreaterThan(0)


    const relationshipTable = screen.getByRole('table', {
      name: 'علاقات الأسئلة بنواتج التعلم وموضوعات المقرر',
    })
    const q2Row = within(relationshipTable)
      .getByRole('rowheader', { name: 'Q2' })
      .closest('tr')!
    fireEvent.click(within(q2Row).getByRole('button', { name: 'عرض تفاصيل الربط' }))
    const dialog = screen.getByRole('dialog')
    expect(
      within(dialog).getByText('The question directly assesses database design.'),
    ).toBeInTheDocument()
    expect(
      within(dialog).queryByText('يشترك السؤال والعنصر المقترح في محتوى مقيم ذي صلة.'),
    ).not.toBeInTheDocument()
  })

  it('keeps successful sections available and retries a failed source resource', () => {
    const { onRetry } = renderSection({
      topics: {
        status: 'error',
        message: 'Topic records unavailable.',
      },
    })

    expect(screen.getAllByText('CLO2').length).toBeGreaterThan(0)
    expect(screen.getByText(/topic records unavailable/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledWith('topics')
  })
})
