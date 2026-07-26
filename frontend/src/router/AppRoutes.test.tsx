import { StrictMode } from 'react'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../api/analyses'
import { ApiError } from '../api/client'
import type {
  AnalysisResponse,
  AnalysisScoreResponse,
  QuestionResponse,
} from '../types/api'
import { AppRoutes } from './AppRoutes'

vi.mock('../api/analyses')

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
      <AppRoutes />
      <LocationControls />
    </MemoryRouter>,
  )
}

function mockResults(): void {
  vi.mocked(analysesApi.listQuestions).mockResolvedValue([QUESTION])
  vi.mocked(analysesApi.listClos).mockResolvedValue([])
  vi.mocked(analysesApi.listTopics).mockResolvedValue([])
  vi.mocked(analysesApi.listFindings).mockResolvedValue([])
  vi.mocked(analysesApi.getAnalysisScore).mockResolvedValue(SCORE)
  vi.mocked(analysesApi.listRecommendations).mockResolvedValue([])
  vi.mocked(analysesApi.listReports).mockResolvedValue([])
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(analysesApi.listAnalyses).mockResolvedValue([])
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
          <AppRoutes />
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
    vi.mocked(analysesApi.listAnalyses).mockRejectedValue(
      new ApiError(503, 'Analysis history is temporarily unavailable.'),
    )

    renderAt('/dashboard')

    expect(await screen.findByText('Analysis history is temporarily unavailable.'))
      .toBeInTheDocument()
    expect(analysesApi.listAnalyses).toHaveBeenCalledTimes(1)
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

  it('redirects an unknown result tab to the safe overview tab', async () => {
    vi.mocked(analysesApi.getAnalysis).mockResolvedValue(COMPLETED_ANALYSIS)

    renderAt('/analyses/analysis-1/results/not-a-tab')

    expect(await screen.findByText('100.00')).toBeInTheDocument()
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
    expect(screen.queryByText('100.00')).not.toBeInTheDocument()
  })

  it('shows a safe fallback for an unknown application route', () => {
    renderAt('/not-a-route')

    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
