import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../api/analyses'
import * as reportsApi from '../api/reports'
import { I18nProvider } from '../i18n/I18nProvider'
import type { AnalysisResponse, AnalysisScoreResponse, ReportResponse } from '../types/api'
import { ReportPreviewRoute } from './ReportPreviewRoute'

vi.mock('../api/analyses')
vi.mock('../api/reports')

const REPORT: ReportResponse = {
  id: 'report-1',
  analysis_id: 'analysis-1',
  format: 'pdf',
  language: 'en',
  kb_version: '1.0',
  capability_version: 'v2-b4',
  score: '80.00',
  score_label: null,
  denominator: 5,
  satisfied_count: 4,
  partially_satisfied_count: 0,
  not_satisfied_count: 1,
  not_verified_count: 0,
  not_applicable_count: 0,
  size_bytes: 1024,
  created_at: '2026-07-01T00:00:00Z',
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

const SCORE: AnalysisScoreResponse = {
  analysis_id: 'analysis-1',
  score: '80.00',
  label: null,
  denominator: 5,
  satisfied_count: 4,
  partially_satisfied_count: 0,
  not_satisfied_count: 1,
  not_verified_count: 0,
  not_applicable_count: 0,
}

function renderPreview() {
  return render(
    <MemoryRouter initialEntries={['/reports/report-1/preview']}>
      <I18nProvider>
        <Routes>
          <Route
            path="/reports/:reportId/preview"
            element={<ReportPreviewRoute />}
          />
        </Routes>
      </I18nProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  window.localStorage.setItem('exam-quality-analyzer-locale', 'en')
  vi.mocked(reportsApi.getReportMetadata).mockResolvedValue(REPORT)
  vi.mocked(analysesApi.downloadReportFile).mockResolvedValue(
    new Blob(['pdf'], { type: 'application/pdf' }),
  )
  vi.mocked(analysesApi.downloadBlob).mockImplementation(() => undefined)
  vi.mocked(analysesApi.getAnalysis).mockResolvedValue(ANALYSIS)
  vi.mocked(analysesApi.listQuestions).mockResolvedValue([])
  vi.mocked(analysesApi.listClos).mockResolvedValue([])
  vi.mocked(analysesApi.listTopics).mockResolvedValue([])
  vi.mocked(analysesApi.listAssessmentRecords).mockResolvedValue([])
  vi.mocked(analysesApi.listFindings).mockResolvedValue([])
  vi.mocked(analysesApi.getAnalysisScore).mockResolvedValue(SCORE)
  vi.mocked(analysesApi.listRecommendations).mockResolvedValue([])
  vi.mocked(analysesApi.listReports).mockResolvedValue([])
  vi.mocked(analysesApi.getRuleCoverage).mockResolvedValue({
    analysis_id: 'analysis-1',
    scope: 'exam_facing_rules',
    total_rules: 0,
    evaluated_rules: 0,
    conditional_capability_gap_rules: 0,
    unsupported_rules: 0,
    not_run_rules: 0,
    runtime_integrity_ok: true,
    entries: [],
  })
  vi.mocked(analysesApi.listSupportingMaterials).mockResolvedValue([])
  vi.mocked(analysesApi.listSupportingMaterialAnnotations).mockResolvedValue([])
  vi.mocked(analysesApi.listDocumentReferences).mockResolvedValue([])
  vi.spyOn(window, 'print').mockImplementation(() => undefined)
})

describe('ReportPreviewRoute', () => {
  it('renders a numbered HTML report document with print and download actions', async () => {
    renderPreview()

    expect(await screen.findByText('1. Report Header')).toBeInTheDocument()
    expect(screen.getByText('2. Executive Summary')).toBeInTheDocument()
    expect(screen.getByText('3. Overall Exam Quality Score')).toBeInTheDocument()
    expect(screen.getByText('4. Status Distribution')).toBeInTheDocument()
    expect(screen.getByText('13. Scope Disclaimer')).toBeInTheDocument()
    expect(screen.queryByText('14. Technical Traceability Appendix')).not.toBeInTheDocument()
    expect(reportsApi.getReportMetadata).toHaveBeenCalledWith('report-1')
    expect(analysesApi.downloadReportFile).toHaveBeenCalledWith('report-1')
    expect(analysesApi.getAnalysis).toHaveBeenCalledWith('analysis-1')
    expect(screen.getAllByText('English Report').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Back to Reports' }))
      .toHaveAttribute('href', '/reports')
    expect(screen.queryByRole('img', { name: /report pdf preview/i })).not.toBeInTheDocument()
    expect(document.querySelector('iframe')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /download pdf/i }))
    expect(analysesApi.downloadBlob).toHaveBeenCalledWith(
      expect.any(Blob),
      'report-en-report-1.pdf',
    )

    fireEvent.click(screen.getByRole('button', { name: /print/i }))
    expect(window.print).toHaveBeenCalled()
  })

  it('does not show provider/model details or Question Type content in the primary report', async () => {
    vi.mocked(analysesApi.listFindings).mockResolvedValue([
      {
        id: 'finding-1',
        analysis_id: 'analysis-1',
        requirement_id: 'REQ011',
        rule_id: 'RULE011',
        recommendation_id: null,
        status: 'Satisfied',
        explanation: 'The question is clear.',
        confidence: 0.9,
        confidence_level: 'High',
        evaluation_details: null,
        evaluator_type: 'semantic_ai',
        ai_provider: 'anthropic',
        ai_model: 'claude',
        prompt_template_version: 'v1',
        kb_version: '1.0',
        created_at: '2026-01-01T00:00:00Z',
        evidence: [],
        requirement_name: 'Clear Task Statement',
        dimension: 'Question Clarity',
        source_type: 'Derived Exam Requirement',
        officiality: 'Derived',
      },
    ])
    renderPreview()

    await screen.findByText('1. Report Header')
    expect(screen.queryByText(/anthropic/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/claude/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/prompt_template_version/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/question type/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/0\.9/)).not.toBeInTheDocument()
    expect(screen.queryByText(/upload revised exam/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/reanalyz/i)).not.toBeInTheDocument()
  })

  it('shows a retryable safe error without exposing storage information', async () => {
    vi.mocked(reportsApi.getReportMetadata)
      .mockRejectedValueOnce(new Error('Report not found.'))
      .mockResolvedValueOnce(REPORT)
    renderPreview()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not preview the report.',
    )
    expect(document.body.textContent).not.toMatch(/storage_key|file:\/\//)
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() =>
      expect(reportsApi.getReportMetadata).toHaveBeenCalledTimes(2),
    )
    expect(await screen.findByText('1. Report Header')).toBeInTheDocument()
  })
})
