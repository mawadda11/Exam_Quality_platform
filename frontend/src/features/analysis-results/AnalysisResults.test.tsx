import { StrictMode, type ReactElement } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { ApiError } from '../../api/client'
import type {
  AnalysisResponse,
  AnalysisScoreResponse,
  FindingResponse,
  QuestionResponse,
  RuleCoverageAuditResponse,
} from '../../types/api'
import { AnalysisResults } from './AnalysisResults'

vi.mock('../../api/analyses')

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
  uploaded_files: [
    {
      id: 'file-1',
      file_type: 'exam',
      original_filename: 'exam.pdf',
      mime_type: 'application/pdf',
      size_bytes: 10,
      sha256_hash: 'a'.repeat(64),
      created_at: '2026-01-01T00:00:00Z',
    },
  ],
  exam_uploaded: true,
  tp153_uploaded: true,
  ready_for_analysis: true,
  capability_version: 'v2-batch4',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
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

const RULE_COVERAGE: RuleCoverageAuditResponse = {
  analysis_id: 'analysis-1',
  scope: 'exam_facing_rules',
  total_rules: 21,
  evaluated_rules: 14,
  conditional_capability_gap_rules: 1,
  unsupported_rules: 6,
  not_run_rules: 0,
  runtime_integrity_ok: true,
  entries: [],
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
  recommendation_id: null,
  status: 'Satisfied',
  explanation: 'The calculated total equals the declared total.',
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
  requirement_name: 'Correct Total Marks',
  dimension: 'Marks and Totals',
  source_type: 'Derived Exam Requirement',
  officiality: 'Derived',
}

function mockSuccessfulLoad(): void {
  vi.mocked(analysesApi.listQuestions).mockResolvedValue([QUESTION])
  vi.mocked(analysesApi.listClos).mockResolvedValue([])
  vi.mocked(analysesApi.listTopics).mockResolvedValue([])
  vi.mocked(analysesApi.listAssessmentRecords).mockResolvedValue([])
  vi.mocked(analysesApi.listFindings).mockResolvedValue([FINDING])
  vi.mocked(analysesApi.getAnalysisScore).mockResolvedValue(SCORE)
  vi.mocked(analysesApi.listRecommendations).mockResolvedValue([])
  vi.mocked(analysesApi.listReports).mockResolvedValue([])
  vi.mocked(analysesApi.getRuleCoverage).mockResolvedValue(RULE_COVERAGE)
}

function resultsTree(element: ReactElement) {
  return <MemoryRouter>{element}</MemoryRouter>
}

beforeEach(() => {
  vi.clearAllMocks()
  mockSuccessfulLoad()
})

describe('AnalysisResults', () => {
  it('shows the real header immediately and independently loads Overview score data', async () => {
    render(resultsTree(<AnalysisResults analysis={ANALYSIS} />))

    expect(screen.getByRole('heading', { level: 1, name: 'Software Engineering' }))
      .toBeInTheDocument()
    expect(screen.getByText('exam.pdf')).toBeInTheDocument()
    expect(screen.getByText(/^loading score…$/i)).toBeInTheDocument()
    expect(
      (
        await screen.findAllByText('100.00%', {
          selector: '.ui-score-ring-value',
        })
      ).length,
    ).toBeGreaterThan(0)
  })

  it('keeps questions available when the score endpoint fails', async () => {
    vi.mocked(analysesApi.getAnalysisScore).mockRejectedValue(
      new ApiError(503, 'Score unavailable.'),
    )
    render(
      resultsTree(<AnalysisResults analysis={ANALYSIS} section="questions" />),
    )

    expect(await screen.findByText('Explain a stack.')).toBeInTheDocument()
    expect(screen.getByText(/score unavailable/i)).toBeInTheDocument()
  })

  it('hides the score and academic results when confirmed questions fail to load', async () => {
    vi.mocked(analysesApi.listQuestions).mockRejectedValue(
      new ApiError(503, 'Questions unavailable.'),
    )
    render(resultsTree(<AnalysisResults analysis={ANALYSIS} />))

    expect(await screen.findAllByText('Analysis incomplete')).not.toHaveLength(0)
    expect(screen.queryByText('100.00%', { selector: '.ui-score-ring-value' }))
      .not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Questions' }))
    expect(await screen.findByText(/questions unavailable/i)).toBeInTheDocument()
  })

  it('retries only the failed resource', async () => {
    vi.mocked(analysesApi.listQuestions)
      .mockRejectedValueOnce(new ApiError(503, 'Questions unavailable.'))
      .mockResolvedValueOnce([QUESTION])
    render(
      resultsTree(<AnalysisResults analysis={ANALYSIS} section="questions" />),
    )

    fireEvent.click(await screen.findByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Explain a stack.')).toBeInTheDocument()
    expect(analysesApi.listQuestions).toHaveBeenCalledTimes(2)
    expect(analysesApi.getAnalysisScore).toHaveBeenCalledTimes(1)
    expect(analysesApi.listFindings).toHaveBeenCalledTimes(1)
  })

  it('deduplicates in-flight resource requests during a Strict Mode remount', async () => {
    render(
      resultsTree(
        <StrictMode>
          <AnalysisResults analysis={ANALYSIS} />
        </StrictMode>,
      ),
    )

    expect(
      (
        await screen.findAllByText('100.00%', {
          selector: '.ui-score-ring-value',
        })
      ).length,
    ).toBeGreaterThan(0)
    expect(analysesApi.listQuestions).toHaveBeenCalledTimes(1)
    expect(analysesApi.listAssessmentRecords).toHaveBeenCalledTimes(1)
    expect(analysesApi.getAnalysisScore).toHaveBeenCalledTimes(1)
    expect(analysesApi.listReports).toHaveBeenCalledTimes(1)
    expect(analysesApi.getRuleCoverage).toHaveBeenCalledTimes(1)
  })

  it('ignores a stale response after the analysis id changes', async () => {
    let resolveOldQuestions: ((questions: QuestionResponse[]) => void) | undefined
    vi.mocked(analysesApi.listQuestions).mockImplementation((analysisId) => {
      if (analysisId === 'analysis-1') {
        return new Promise((resolve) => {
          resolveOldQuestions = resolve
        })
      }
      return Promise.resolve([
        {
          ...QUESTION,
          id: 'q-2',
          analysis_id: 'analysis-2',
          number_label: 'Q2',
          question_text: 'Explain a queue.',
        },
      ])
    })
    const { rerender } = render(
      resultsTree(
        <AnalysisResults analysis={ANALYSIS} section="questions" />,
      ),
    )
    rerender(
      resultsTree(
        <AnalysisResults
          analysis={{ ...ANALYSIS, id: 'analysis-2' }}
          section="questions"
        />,
      ),
    )

    expect(await screen.findByText('Explain a queue.')).toBeInTheDocument()
    resolveOldQuestions?.([QUESTION])
    await waitFor(() =>
      expect(screen.queryByText('Explain a stack.')).not.toBeInTheDocument(),
    )
  })

  it('keeps methodology at page level and hides technical provenance from Faculty', async () => {
    vi.mocked(analysesApi.listFindings).mockResolvedValue([
      {
        ...FINDING,
        evaluator_type: 'semantic_ai',
        confidence: 0.84,
        confidence_level: 'High',
        evaluation_details: {
          schema_version: 1,
          decision: 'Satisfied',
          evidence_used: [],
          reasoning: 'The semantic evaluator confirmed the governed requirement.',
          recommendation: null,
          confidence_basis: ['All required items were judged.'],
          item_judgments: [],
          retrieved_knowledge_ids: ['REQ018', 'RULE018'],
        },
        ai_provider: 'fake',
        ai_model: 'fake-semantic-v1',
        prompt_template_version: 'semantic-rule-v1',
        kb_version: '1.0.0',
      },
    ])
    render(
      resultsTree(
        <AnalysisResults
          analysis={ANALYSIS}
          section="findings-recommendations"
        />,
      ),
    )

    fireEvent.click(await screen.findByText(/satisfied findings \(1\)/i))
    expect(
      screen.getByRole('link', {
        name: 'How does the platform determine results?',
      }),
    ).toHaveAttribute('href', '/evaluation-scope#evaluation-methods')
    expect(screen.queryByText('How was this result determined?'))
      .not.toBeInTheDocument()
    expect(screen.queryByText('Evidence reliability')).not.toBeInTheDocument()
    expect(screen.queryByText('fake')).not.toBeInTheDocument()
    expect(screen.queryByText('fake-semantic-v1')).not.toBeInTheDocument()
    expect(screen.queryByText('semantic-rule-v1')).not.toBeInTheDocument()
    expect(screen.queryByText('v2-batch4')).not.toBeInTheDocument()
    expect(screen.queryByText('1.0.0')).not.toBeInTheDocument()
    expect(screen.queryByText(/REQ018|RULE018/)).not.toBeInTheDocument()
    expect(screen.queryByText(/audit and methodology details/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/84%/i)).not.toBeInTheDocument()
  })
})
