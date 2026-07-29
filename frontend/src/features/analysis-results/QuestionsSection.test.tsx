import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { I18nProvider } from '../../i18n/I18nProvider'
import type { QuestionResponse } from '../../types/api'
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

const CHILDREN: QuestionResponse[] = [
  {
    ...PARENT,
    id: 'child-a',
    parent_question_id: PARENT.id,
    number_label: 'Q1(a)',
    question_text: 'اكتب دالة hash table.',
    marks: 4,
    sequence: 2,
  },
  {
    ...PARENT,
    id: 'child-b',
    parent_question_id: PARENT.id,
    number_label: 'Q1(b)',
    question_text: 'Calculate x = 2 + 3.',
    marks: 6,
    sequence: 3,
  },
]

function renderSection() {
  return render(
    <I18nProvider>
      <QuestionsSection questions={[PARENT, ...CHILDREN]} />
    </I18nProvider>,
  )
}

beforeEach(() => {
  window.localStorage.clear()
  window.localStorage.setItem('exam-quality-analyzer-locale', 'en')
})

describe('QuestionsSection', () => {
  it('shows only the core columns and omits the structural parent row', () => {
    renderSection()

    const table = screen.getByRole('table', { name: 'Extracted questions' })
    expect(
      within(table).getAllByRole('columnheader').map((header) => header.textContent),
    ).toEqual(['Question', 'Page', 'Marks', 'Text'])
    expect(within(table).queryByText('Q1')).not.toBeInTheDocument()
    expect(within(table).getByText('Q1(a)').closest('bdi')).toBeInTheDocument()
    expect(within(table).getByText('Q1(b)').closest('bdi')).toBeInTheDocument()
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(screen.queryByText(/Question Type/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Distribution/i)).not.toBeInTheDocument()
  })

  it('preserves source text direction and localized RTL headers', () => {
    window.localStorage.setItem('exam-quality-analyzer-locale', 'ar')
    renderSection()

    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    expect(screen.getByText(CHILDREN[0].question_text)).toHaveAttribute('dir', 'auto')
    const table = screen.getByRole('table', { name: 'الأسئلة المستخرجة' })
    expect(
      within(table).getAllByRole('columnheader').map((header) => header.textContent),
    ).toEqual(['السؤال', 'الصفحة', 'الدرجات', 'النص'])
  })
})
