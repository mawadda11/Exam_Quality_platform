import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { QuestionResponse } from '../../types/api'
import { QuestionsSection } from './QuestionsSection'

const QUESTION: QuestionResponse = {
  id: 'question-1',
  analysis_id: 'analysis-1',
  parent_question_id: null,
  number_label: 'س1',
  question_text: 'اشرح وظيفة hash table في البرنامج.',
  page_number: 2,
  marks: 5,
  sequence: 1,
  confidence: 0.95,
  geometry: null,
  created_at: '2026-07-26T00:00:00Z',
}

describe('QuestionsSection', () => {
  it('uses bidi isolation for identifiers and automatic direction for source text', () => {
    render(<QuestionsSection questions={[QUESTION]} />)

    expect(screen.getByText('س1').closest('bdi')).toBeInTheDocument()
    expect(screen.getByText(QUESTION.question_text)).toHaveAttribute('dir', 'auto')
    expect(screen.getByRole('table', { name: 'Extracted questions' })).toBeInTheDocument()
  })
})
