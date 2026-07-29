import { StrictMode } from 'react'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../api/analyses'
import * as authApi from '../api/auth'
import { setStoredAccessToken } from '../api/authToken'
import { ApiError } from '../api/client'
import { AuthProvider } from '../features/auth/AuthProvider'
import type {
  AnalysisResponse,
  AnalysisScoreResponse,
  ExtractionReviewResponse,
  QuestionResponse,
} from '../types/api'
import { AppRoutes } from './AppRoutes'

vi.mock('../api/analyses')
vi.mock('../api/auth')

const QUEUED_ANALYSIS: AnalysisResponse = {
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
  state: 'queued',
  owner_user_id: 'user-1',
  predecessor_analysis_id: null,
  uploaded_files: [],
  exam_uploaded: false,
  tp153_uploaded: false,
  ready_for_analysis: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const COMPLETED_ANALYSIS: AnalysisResponse = {
  ...QUEUED_ANALYSIS,
  state: 'completed',
  exam_uploaded: true,
  tp153_uploaded: true,
  ready_for_analysis: true,
}

const QUESTION: QuestionResponse = {
  id: 'question-1',
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

const EXTRACTION_REVIEW: ExtractionReviewResponse = {
  analysis_id: 'analysis-1',
  revision_id: 'review-revision-1',
  revision_number: 1,
  created_at: '2026-07-26T00:00:00Z',
  snapshot: {
    schema_version: 1,
    questions: [
      {
        source_record_id: 'question-source-1',
        included: true,
        parent_source_record_id: null,
        number_label: 'Q1',
        question_text: 'Explain a stack.',
        page_number: 1,
        marks: 5,
        sequence: 1,
        extraction_confidence: 0.9,
        geometry: null,
      },
    ],
    evidence: [],
    clos: [],
    topics: [],
    assessment_records: [],
  },
  original_snapshot: {
    schema_version: 1,
    questions: [
      {
        source_record_id: 'question-source-1',
        included: true,
        parent_source_record_id: null,
        number_label: 'Q1',
        question_text: 'Explain a stack.',
        page_number: 1,
        marks: 5,
        sequence: 1,
        extraction_confidence: 0.9,
        geometry: null,
      },
    ],
    evidence: [],
    clos: [],
    topics: [],
    assessment_records: [],
  },
  confirmed_revision_id: null,
  is_confirmed: false,
  can_edit: true,
  can_confirm: true,
  warnings: [],
  confirmation_blockers: [],
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

function LocationControls() {
  const location = useLocation()
  const navigate = useNavigate()
  return (
    <div>
      <output aria-label="Current route">{location.pathname}</output>
      <button type="button" onClick={() => navigate(-1)}>
        Browser Back
      </button>
      <button type="button" onClick={() => navigate(1)}>
        Browser Forward
      </button>
    </div>
  )
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <AppRoutes />
        <LocationControls />
      </AuthProvider>
    </MemoryRouter>,
  )
}

function mockResults(): void {
  vi.mocked(analysesApi.listQuestions).mockResolvedValue([QUESTION])
  vi.mocked(analysesApi.listClos).mockResolvedValue([])
  vi.mocked(analysesApi.listTopics).mockResolvedValue([])
  vi.mocked(analysesApi.listAssessmentRecords).mockResolvedValue([])
  vi.mocked(analysesApi.listFindings).mockResolvedValue([])
  vi.mocked(analysesApi.getAnalysisScore).mockResolvedValue(SCORE)
  vi.mocked(analysesApi.listRecommendations).mockResolvedValue([])
  vi.mocked(analysesApi.listReports).mockResolvedValue([])
}

beforeEach(() => {
  vi.clearAllMocks()
  window.localStorage.clear()
  setStoredAccessToken('test-access-token')
  vi.mocked(authApi.getCurrentFaculty).mockResolvedValue({
    id: 'user-1',
    email: 'faculty@university.edu',
    display_name: 'Dr Faculty',
    institution: 'Example University',
    department: 'Computing',
    user_type: 'Faculty Member',
    preferred_language: 'en',
    email_verified: false,
    created_at: '2026-01-01T00:00:00Z',
  })
  vi.mocked(analysesApi.listAnalyses).mockResolvedValue([])
  vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(EXTRACTION_REVIEW)
  mockResults()
})

describe('AppRoutes', () => {
  it('redirects the root route to the dashboard', async () => {
    renderAt('/')

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByLabelText('Current route')).toHaveTextContent('/dashboard')
  })

  it('builds dashboard metrics from one history request without score or detail calls', async () => {
    vi.mocked(analysesApi.listAnalyses).mockResolvedValue([
      COMPLETED_ANALYSIS,
      {
        ...QUEUED_ANALYSIS,
        id: 'analysis-2',
        state: 'validating',
        predecessor_analysis_id: 'analysis-1',
      },
      { ...QUEUED_ANALYSIS, id: 'analysis-3' },
    ])

    renderAt('/dashboard')

    const totalCard = (await screen.findByRole('heading', {
      name: 'Total analyses',
    })).closest('article')
    const completedCard = screen
      .getByRole('heading', { name: 'Completed analyses' })
      .closest('article')
    const reanalysisCard = screen
      .getByRole('heading', { name: 'Linked reanalyses' })
      .closest('article')

    expect(totalCard && within(totalCard).getByText('3')).toBeInTheDocument()
    expect(completedCard && within(completedCard).getByText('1')).toBeInTheDocument()
    expect(reanalysisCard && within(reanalysisCard).getByText('1')).toBeInTheDocument()
    expect(analysesApi.listAnalyses).toHaveBeenCalledTimes(1)
    expect(analysesApi.getAnalysis).not.toHaveBeenCalled()
    expect(analysesApi.getAnalysisScore).not.toHaveBeenCalled()
  })

  it('deduplicates the dashboard request during the development Strict Mode remount', async () => {
    render(
      <StrictMode>
        <MemoryRouter initialEntries={['/dashboard']}>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </MemoryRouter>
      </StrictMode>,
    )

    expect(await screen.findByRole('heading', { name: 'Total analyses' }))
      .toBeInTheDocument()
    expect(analysesApi.listAnalyses).toHaveBeenCalledTimes(1)
  })

  it('loads the full history with one list request and exact backend state labels', async () => {
    vi.mocked(analysesApi.listAnalyses).mockResolvedValue([
      { ...QUEUED_ANALYSIS, state: 'extracting_tp153' },
    ])

    renderAt('/analyses')

    expect(await screen.findByLabelText('Processing state: extracting_tp153'))
      .toHaveTextContent('extracting_tp153')
    expect(analysesApi.listAnalyses).toHaveBeenCalledTimes(1)
    expect(analysesApi.getAnalysisScore).not.toHaveBeenCalled()
  })

  it('shows an API-derived dashboard error without requesting metric details', async () => {
    vi.mocked(analysesApi.listAnalyses)
      .mockRejectedValueOnce(
        new ApiError(503, 'Analysis history is temporarily unavailable.'),
      )
      .mockResolvedValueOnce([COMPLETED_ANALYSIS])

    renderAt('/dashboard')

    expect(await screen.findByText('Analysis history is temporarily unavailable.'))
      .toBeInTheDocument()
    expect(analysesApi.listAnalyses).toHaveBeenCalledTimes(1)
    expect(analysesApi.getAnalysis).not.toHaveBeenCalled()
    expect(analysesApi.getAnalysisScore).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Retry dashboard' }))
    expect(await screen.findByRole('heading', { name: 'Total analyses' }))
      .toBeInTheDocument()
    expect(analysesApi.listAnalyses).toHaveBeenCalledTimes(2)
    expect(analysesApi.getAnalysis).not.toHaveBeenCalled()
    expect(analysesApi.getAnalysisScore).not.toHaveBeenCalled()
  })

  it('retries only a failed analysis-history request', async () => {
    vi.mocked(analysesApi.listAnalyses)
      .mockRejectedValueOnce(new ApiError(503, 'History unavailable.'))
      .mockResolvedValueOnce([QUEUED_ANALYSIS])

    renderAt('/analyses')

    fireEvent.click(
      await screen.findByRole('button', { name: 'Retry analyses' }),
    )

    expect(await screen.findByText('CPIT-450')).toBeInTheDocument()
    expect(analysesApi.listAnalyses).toHaveBeenCalledTimes(2)
    expect(analysesApi.getAnalysis).not.toHaveBeenCalled()
    expect(analysesApi.getAnalysisScore).not.toHaveBeenCalled()
  })

  it('loads a deep-linked analysis once and preserves the selected results tab', async () => {
    vi.mocked(analysesApi.getAnalysis).mockResolvedValue(COMPLETED_ANALYSIS)

    renderAt('/analyses/analysis-1/results/questions')

    expect(await screen.findByText('Explain a stack.')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Questions' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(analysesApi.getAnalysis).toHaveBeenCalledTimes(1)
  })

  it('uses URL history for results tabs and supports browser back navigation', async () => {
    vi.mocked(analysesApi.getAnalysis).mockResolvedValue(COMPLETED_ANALYSIS)
    renderAt('/analyses/analysis-1/results/questions')
    await screen.findByText('Explain a stack.')

    fireEvent.click(screen.getByRole('tab', { name: 'Report' }))
    expect(screen.getByLabelText('Current route')).toHaveTextContent(
      '/analyses/analysis-1/results/report',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Browser Back' }))
    await waitFor(() =>
      expect(screen.getByLabelText('Current route')).toHaveTextContent(
        '/analyses/analysis-1/results/questions',
      ),
    )
    expect(screen.getByRole('tab', { name: 'Questions' })).toHaveAttribute(
      'aria-selected',
      'true',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Browser Forward' }))
    await waitFor(() =>
      expect(screen.getByLabelText('Current route')).toHaveTextContent(
        '/analyses/analysis-1/results/report',
      ),
    )
    expect(screen.getByRole('tab', { name: 'Report' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })

  it('has no Question Types tab or route', async () => {
    vi.mocked(analysesApi.getAnalysis).mockResolvedValue(COMPLETED_ANALYSIS)
    renderAt('/analyses/analysis-1/results/question-types')

    await waitFor(() =>
      expect(screen.getByLabelText('Current route')).toHaveTextContent(
        '/analyses/analysis-1/results/overview',
      ),
    )
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(
      screen.queryByRole('tab', { name: /Question Types/i }),
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/Question Type Distribution/i))
      .not.toBeInTheDocument()
  })

  it('preserves result-tab focus while the tab URL changes', async () => {
    vi.mocked(analysesApi.getAnalysis).mockResolvedValue(COMPLETED_ANALYSIS)
    renderAt('/analyses/analysis-1/results/questions')
    await screen.findByText('Explain a stack.')

    const questionsTab = screen.getByRole('tab', { name: 'Questions' })
    questionsTab.focus()
    fireEvent.keyDown(questionsTab, { key: 'ArrowRight' })

    const alignmentTab = screen.getByRole('tab', {
      name: 'Alignment & Coverage',
    })
    await waitFor(() => expect(alignmentTab).toHaveFocus())
    expect(screen.getByLabelText('Current route')).toHaveTextContent(
      '/analyses/analysis-1/results/alignment-coverage',
    )
  })

  it('reuses the shared analysis load while moving from start to progress', async () => {
    const ready = {
      ...QUEUED_ANALYSIS,
      exam_uploaded: true,
      tp153_uploaded: true,
      ready_for_analysis: true,
    }
    vi.mocked(analysesApi.getAnalysis).mockResolvedValue(ready)
    vi.mocked(analysesApi.runAnalysis).mockResolvedValue({
      ...ready,
      state: 'validating',
    })

    renderAt('/analyses/analysis-1/start')
    fireEvent.click(await screen.findByRole('button', { name: /start analysis/i }))

    await waitFor(() =>
      expect(screen.getByLabelText('Current route')).toHaveTextContent(
        '/analyses/analysis-1/progress',
      ),
    )
    expect(analysesApi.getAnalysis).toHaveBeenCalledTimes(1)
    expect(screen.getByText('validating', { selector: 'strong' })).toBeInTheDocument()
  })

  it('keeps a ready queued analysis on documents until the user explicitly continues and starts', async () => {
    const ready = {
      ...QUEUED_ANALYSIS,
      exam_uploaded: true,
      tp153_uploaded: true,
      ready_for_analysis: true,
      uploaded_files: [
        {
          id: 'exam-file',
          file_type: 'exam' as const,
          original_filename: 'exam.pdf',
          mime_type: 'application/pdf',
          size_bytes: 1024,
          sha256_hash: 'a'.repeat(64),
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'tp153-file',
          file_type: 'tp153' as const,
          original_filename: 'tp153.pdf',
          mime_type: 'application/pdf',
          size_bytes: 2048,
          sha256_hash: 'b'.repeat(64),
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    }
    vi.mocked(analysesApi.getAnalysis).mockResolvedValue(ready)

    renderAt('/analyses/analysis-1/documents')

    expect(
      await screen.findByRole('link', { name: /continue to review and start/i }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Current route')).toHaveTextContent(
      '/analyses/analysis-1/documents',
    )
    expect(analysesApi.runAnalysis).not.toHaveBeenCalled()

    fireEvent.click(
      screen.getByRole('link', { name: /continue to review and start/i }),
    )

    expect(await screen.findByRole('heading', { level: 1, name: 'Review and Start' }))
      .toBeInTheDocument()
    expect(screen.getByText('exam.pdf')).toBeInTheDocument()
    expect(screen.getByText('tp153.pdf')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument()
    expect(analysesApi.runAnalysis).not.toHaveBeenCalled()
    expect(analysesApi.getAnalysis).toHaveBeenCalledTimes(1)
  })

  it('loads a newly created reanalysis before applying its child-route guards', async () => {
    const reanalysis = {
      ...QUEUED_ANALYSIS,
      id: 'analysis-2',
      predecessor_analysis_id: 'analysis-1',
    }
    vi.mocked(analysesApi.getAnalysis)
      .mockResolvedValueOnce(COMPLETED_ANALYSIS)
      .mockResolvedValueOnce(reanalysis)
    vi.mocked(analysesApi.createReanalysis).mockResolvedValue(reanalysis)

    renderAt('/analyses/analysis-1/results/overview')
    fireEvent.click(
      await screen.findByRole('button', { name: /create reanalysis/i }),
    )

    expect(await screen.findByLabelText(/examination pdf/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Current route')).toHaveTextContent(
      '/analyses/analysis-2/documents',
    )
    expect(analysesApi.getAnalysis).toHaveBeenNthCalledWith(1, 'analysis-1')
    expect(analysesApi.getAnalysis).toHaveBeenNthCalledWith(2, 'analysis-2')
  })

  it('guards results for a queued analysis and redirects to document upload', async () => {
    vi.mocked(analysesApi.getAnalysis).mockResolvedValue(QUEUED_ANALYSIS)

    renderAt('/analyses/analysis-1/results/questions')

    expect(await screen.findByLabelText(/examination pdf/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Current route')).toHaveTextContent(
      '/analyses/analysis-1/documents',
    )
    expect(analysesApi.listQuestions).not.toHaveBeenCalled()
  })

  it('routes review_ready analyses to the dedicated extraction-review workspace', async () => {
    vi.mocked(analysesApi.getAnalysis).mockResolvedValue({
      ...COMPLETED_ANALYSIS,
      state: 'review_ready',
    })

    renderAt('/analyses/analysis-1/results/overview')

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Review Extracted Evidence' }),
    ).toBeInTheDocument()
    expect(
  await screen.findByDisplayValue('Explain a stack.'),
).toBeInTheDocument()
    expect(screen.getByLabelText('Current route')).toHaveTextContent(
      '/analyses/analysis-1/review',
    )
    expect(analysesApi.getExtractionReview).toHaveBeenCalledWith('analysis-1')
    expect(analysesApi.getAnalysisProgress).not.toHaveBeenCalled()
    expect(analysesApi.listFindings).not.toHaveBeenCalled()
  })

  it('redirects an unknown result tab to the safe overview tab', async () => {
    vi.mocked(analysesApi.getAnalysis).mockResolvedValue(COMPLETED_ANALYSIS)

    renderAt('/analyses/analysis-1/results/not-a-tab')

    expect((await screen.findAllByText('100.00%')).length).toBeGreaterThan(0)
    expect(screen.getByLabelText('Current route')).toHaveTextContent(
      '/analyses/analysis-1/results/overview',
    )
  })

  it('shows the safe API detail for an unknown or inaccessible analysis', async () => {
    vi.mocked(analysesApi.getAnalysis).mockRejectedValue(
      new ApiError(404, 'Analysis not found.'),
    )

    renderAt('/analyses/missing/results/overview')

    expect(await screen.findByText('Analysis not found.')).toBeInTheDocument()
    expect(screen.queryByText('100.00%')).not.toBeInTheDocument()
  })

  it('retries only a failed shared analysis request', async () => {
    vi.mocked(analysesApi.getAnalysis)
      .mockRejectedValueOnce(new ApiError(503, 'Analysis temporarily unavailable.'))
      .mockResolvedValueOnce(COMPLETED_ANALYSIS)

    renderAt('/analyses/analysis-1/results/overview')

    fireEvent.click(
      await screen.findByRole('button', { name: 'Retry analysis' }),
    )

    expect(
      await screen.findByRole('heading', { name: 'Software Engineering' }),
    ).toBeInTheDocument()
    expect(analysesApi.getAnalysis).toHaveBeenCalledTimes(2)
  })

  it('shows a safe fallback for an unknown application route', async () => {
    renderAt('/not-a-route')

    expect(
      await screen.findByRole('heading', { name: 'Page not found' }),
    ).toBeInTheDocument()
  })
})
