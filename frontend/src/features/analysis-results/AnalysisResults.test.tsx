import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { AnalysisResponse, AnalysisScoreResponse, FindingResponse, QuestionResponse } from '../../types/api'
import { AnalysisResults } from './AnalysisResults'

vi.mock('../../api/analyses')

const ANALYSIS: AnalysisResponse = {
  id: 'analysis-1',
  course: { id: 'course-1', code: 'CPIT-450', name: 'Software Engineering', department: null, program: null },
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

const SCORE: AnalysisScoreResponse = {
  analysis_id: 'analysis-1',
  score: '100.00',
  label: null,
  denominator: 1,
  satisfied_count: 1,
  partially_satisfied_count: 0,
  not_satisfied_count: 0,
  not_verified_count: 0,
  not_applicable_count: 0,
}

const QUESTION: QuestionResponse = {
  id: 'q-1',
  analysis_id: 'analysis-1',
  parent_question_id: null,
  number_label: 'Q1',
  question_text: 'Explain a stack.',
  page_number: 1,
  marks: 5,
  sequence: 1,
  confidence: 1,
  geometry: null,
  created_at: '2026-01-01T00:00:00Z',
}

const FINDING: FindingResponse = {
  id: 'finding-1',
  analysis_id: 'analysis-1',
  requirement_id: 'REQ018',
  rule_id: 'RULE018',
  status: 'Satisfied',
  explanation: 'The calculated total equals the declared total.',
  confidence: 1,
  evaluator_type: 'deterministic_rule',
  created_at: '2026-01-01T00:00:00Z',
  evidence: [],
  requirement_name: 'Correct Total Marks',
  dimension: 'Marks and Totals',
  source_type: 'Derived Exam Requirement',
  officiality: 'Derived',
}

function mockSuccessfulLoad(): void {
  vi.mocked(analysesApi.listQuestions).mockResolvedValue([QUESTION])
  vi.mocked(analysesApi.listClos).mockResolvedValue([])
  vi.mocked(analysesApi.listTopics).mockResolvedValue([])
  vi.mocked(analysesApi.listFindings).mockResolvedValue([FINDING])
  vi.mocked(analysesApi.getAnalysisScore).mockResolvedValue(SCORE)
  vi.mocked(analysesApi.listRecommendations).mockResolvedValue([])
  vi.mocked(analysesApi.listReports).mockResolvedValue([])
}

beforeEach(() => {
  vi.mocked(analysesApi.listQuestions).mockReset()
  vi.mocked(analysesApi.listClos).mockReset()
  vi.mocked(analysesApi.listTopics).mockReset()
  vi.mocked(analysesApi.listFindings).mockReset()
  vi.mocked(analysesApi.getAnalysisScore).mockReset()
  vi.mocked(analysesApi.listRecommendations).mockReset()
  vi.mocked(analysesApi.listReports).mockReset()
})

describe('AnalysisResults', () => {
  it('shows a loading state and then the Overview section by default', async () => {
    mockSuccessfulLoad()
    render(<AnalysisResults analysis={ANALYSIS} />)

    expect(screen.getByText(/loading results/i)).toBeInTheDocument()
    expect(await screen.findByText('100.00')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Overview' })).toHaveClass('results-nav-active')
  })

  it('switches sections when a nav button is clicked', async () => {
    mockSuccessfulLoad()
    render(<AnalysisResults analysis={ANALYSIS} />)
    await screen.findByText('100.00')

    fireEvent.click(screen.getByRole('button', { name: 'Questions' }))

    expect(screen.getByText('Explain a stack.')).toBeInTheDocument()
    expect(screen.queryByText('100.00')).not.toBeInTheDocument()
  })

  it('shows the Report section with a Generate Report action and an honest empty state', async () => {
    mockSuccessfulLoad()
    render(<AnalysisResults analysis={ANALYSIS} />)
    await screen.findByText('100.00')

    fireEvent.click(screen.getByRole('button', { name: 'Report' }))

    expect(screen.getByRole('button', { name: /generate report/i })).toBeInTheDocument()
    expect(screen.getByText(/no reports have been generated yet/i)).toBeInTheDocument()
  })

  it('shows an error message instead of a partial or broken view when a fetch fails', async () => {
    vi.mocked(analysesApi.listQuestions).mockRejectedValue(new ApiError(500, 'Server unavailable.'))
    vi.mocked(analysesApi.listClos).mockResolvedValue([])
    vi.mocked(analysesApi.listTopics).mockResolvedValue([])
    vi.mocked(analysesApi.listFindings).mockResolvedValue([])
    vi.mocked(analysesApi.getAnalysisScore).mockResolvedValue(SCORE)
    vi.mocked(analysesApi.listRecommendations).mockResolvedValue([])
    vi.mocked(analysesApi.listReports).mockResolvedValue([])

    render(<AnalysisResults analysis={ANALYSIS} />)

    expect(await screen.findByText(/server unavailable/i)).toBeInTheDocument()
  })
})
