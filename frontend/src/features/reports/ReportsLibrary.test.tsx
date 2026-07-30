import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import * as reportsApi from '../../api/reports'
import { I18nProvider } from '../../i18n/I18nProvider'
import type {
  ReportLibraryItemResponse,
  ReportLibraryPageResponse,
  ReportResponse,
} from '../../types/api'
import { ReportsRoute } from '../../routes/ReportsRoute'

vi.mock('../../api/analyses')
vi.mock('../../api/reports')

const ANALYSIS = {
  id: 'analysis-1',
  course_code: 'CPIT-450',
  course_name: 'Software Engineering',
  exam_type: 'Midterm' as const,
  term: '2026 Spring',
  state: 'completed' as const,
  capability_version: 'v2-b4',
  predecessor_analysis_id: null,
  created_at: '2026-07-01T08:00:00Z',
  updated_at: '2026-07-01T09:00:00Z',
}

const REPORT: ReportResponse = {
  id: 'report-1',
  analysis_id: ANALYSIS.id,
  format: 'pdf',
  language: 'en',
  kb_version: '1.0',
  capability_version: 'v2-b4',
  score: '82.50',
  score_label: null,
  denominator: 10,
  satisfied_count: 7,
  partially_satisfied_count: 2,
  not_satisfied_count: 1,
  not_verified_count: 0,
  not_applicable_count: 0,
  size_bytes: 2048,
  created_at: '2026-07-03T10:30:00Z',
}

function item(
  overrides: Partial<ReportLibraryItemResponse> = {},
): ReportLibraryItemResponse {
  return {
    status: 'available',
    analysis: ANALYSIS,
    report: REPORT,
    ...overrides,
  }
}

function page(
  items: ReportLibraryItemResponse[] = [],
  overrides: Partial<ReportLibraryPageResponse> = {},
): ReportLibraryPageResponse {
  return {
    items,
    total: items.length,
    page: 1,
    page_size: 12,
    total_pages: items.length ? 1 : 0,
    ...overrides,
  }
}

function renderReports() {
  return render(
    <MemoryRouter>
      <I18nProvider>
        <ReportsRoute />
      </I18nProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  window.localStorage.setItem('exam-quality-analyzer-locale', 'en')
  vi.mocked(reportsApi.listReportLibrary).mockResolvedValue(page())
  vi.mocked(analysesApi.generateReport).mockResolvedValue(REPORT)
  vi.mocked(analysesApi.downloadReportFile).mockResolvedValue(
    new Blob(['pdf'], { type: 'application/pdf' }),
  )
  vi.mocked(analysesApi.downloadBlob).mockImplementation(() => undefined)
})

describe('ReportsLibrary', () => {
  it('announces a loading skeleton instead of an empty page', () => {
    vi.mocked(reportsApi.listReportLibrary).mockReturnValue(
      new Promise(() => undefined),
    )
    const { container } = renderReports()

    expect(screen.getByRole('status', { name: 'Loading reports' }))
      .toHaveAttribute('aria-busy', 'true')
    expect(container.querySelectorAll('.reports-card-skeleton')).toHaveLength(6)
  })

  it('renders authoritative card states, scores, metadata, and exact actions', async () => {
    vi.mocked(reportsApi.listReportLibrary).mockResolvedValue(
      page([
        item(),
        item({
          status: 'insufficient_evidence',
          analysis: {
            ...ANALYSIS,
            id: 'analysis-2',
            course_code: 'CPIT-451',
          },
          report: {
            ...REPORT,
            id: 'report-2',
            analysis_id: 'analysis-2',
            language: 'ar',
            score: null,
            score_label: 'Insufficient Evidence',
            denominator: 0,
          },
        }),
        item({
          status: 'not_generated',
          analysis: {
            ...ANALYSIS,
            id: 'analysis-3',
            course_code: 'CPIT-452',
          },
          report: null,
        }),
        item({
          status: 'outdated',
          analysis: {
            ...ANALYSIS,
            id: 'analysis-4',
            course_code: 'CPIT-453',
            predecessor_analysis_id: 'analysis-0',
          },
          report: {
            ...REPORT,
            id: 'report-4',
            analysis_id: 'analysis-4',
            capability_version: 'older',
          },
        }),
      ]),
    )

    const { container } = renderReports()

    expect(await screen.findByRole('heading', { name: 'Reports' }))
      .toBeInTheDocument()
    expect(screen.getAllByText('82.50%')).toHaveLength(2)
    expect(screen.getAllByText('Insufficient Evidence').length).toBeGreaterThan(0)
    expect(screen.queryByText('0%')).not.toBeInTheDocument()
    expect(screen.getByText('report-1')).toBeInTheDocument()
    expect(screen.getAllByText('English Report').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Arabic Report').length).toBeGreaterThan(0)
    expect(
      container.querySelector('[data-report-status="not_generated"]'),
    ).toHaveTextContent('Not Generated')
    expect(
      container.querySelector('[data-report-status="outdated"]'),
    ).toHaveTextContent('Outdated')
    expect(
      screen.getByRole('article', {
        name: /CPIT-453.*Software Engineering/,
      }),
    ).toHaveTextContent('Linked reanalysis')

    const generatedCard = screen.getByRole('article', {
      name: /CPIT-450.*Software Engineering/,
    })
    expect(within(generatedCard).getByText('Report identifier')).toBeInTheDocument()
    expect(within(generatedCard).getByText('Generated')).toBeInTheDocument()
    expect(within(generatedCard).getByText('Overall score')).toBeInTheDocument()

    const notGeneratedCard = screen.getByRole('article', {
      name: /CPIT-452.*Software Engineering/,
    })
    expect(notGeneratedCard).toHaveTextContent('Midterm')
    expect(notGeneratedCard).toHaveTextContent('2026 Spring')
    expect(within(notGeneratedCard).getByText('Not Generated')).toBeInTheDocument()
    expect(within(notGeneratedCard).queryByText('Report identifier'))
      .not.toBeInTheDocument()
    expect(within(notGeneratedCard).queryByText('Generated')).not.toBeInTheDocument()
    expect(within(notGeneratedCard).queryByText('Overall score')).not.toBeInTheDocument()
    expect(within(notGeneratedCard).getByLabelText('Report language'))
      .toBeInTheDocument()
    expect(within(notGeneratedCard).getByRole('button', { name: 'Generate Report' }))
      .toBeEnabled()
    expect(container).not.toHaveTextContent('Not available')

    expect(screen.getAllByRole('link', { name: 'View Analysis' })).toHaveLength(4)
    expect(screen.getAllByRole('link', { name: 'Preview Report' })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: 'Download PDF' })).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Generate Report' })).toBeEnabled()
    expect(
      screen.getByRole('button', { name: 'Generate Updated Report' }),
    ).toBeEnabled()
    expect(container.querySelector('.reports-library-grid')).toBeInTheDocument()
    expect(container.textContent).not.toMatch(/Demo Faculty|RPT-ANL-2026|Valid/)
  })

  it('excludes incomplete analyses and never exposes report generation for them', async () => {
    vi.mocked(reportsApi.listReportLibrary).mockResolvedValue(
      page([
        item({
          status: 'not_generated',
          analysis: {
            ...ANALYSIS,
            id: 'analysis-incomplete',
            course_code: 'CPIT-499',
            course_name: 'Incomplete Systems',
            state: 'extracting_exam',
          },
          report: null,
        }),
      ]),
    )

    renderReports()

    expect(
      await screen.findByRole('heading', { name: 'No reports available yet' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('Incomplete Systems')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Generate Report' }))
      .not.toBeInTheDocument()
    expect(
      screen.getAllByRole('link', { name: 'View incomplete analyses' })[0],
    ).toHaveAttribute('href', '/analyses')
  })

  it('generates the selected language, prevents duplication, and exposes real failure retry', async () => {
    vi.mocked(reportsApi.listReportLibrary).mockResolvedValue(
      page([
        item({
          status: 'not_generated',
          report: null,
        }),
      ]),
    )
    vi.mocked(analysesApi.generateReport)
      .mockRejectedValueOnce(new Error('Report renderer unavailable.'))
      .mockResolvedValueOnce({ ...REPORT, language: 'ar' })

    renderReports()
    const card = await screen.findByRole('article', {
      name: /CPIT-450.*Software Engineering/,
    })
    fireEvent.change(within(card).getByLabelText('Report language'), {
      target: { value: 'ar' },
    })
    fireEvent.click(within(card).getByRole('button', { name: 'Generate Report' }))

    expect(await within(card).findByText('Generation Failed')).toBeInTheDocument()
    expect(
      within(card).getByRole('button', { name: 'Retry Generation' }),
    ).toBeEnabled()
    expect(analysesApi.generateReport).toHaveBeenCalledWith('analysis-1', 'ar')

    fireEvent.click(
      within(card).getByRole('button', { name: 'Retry Generation' }),
    )
    await waitFor(() =>
      expect(analysesApi.generateReport).toHaveBeenCalledTimes(2),
    )
    expect(analysesApi.generateReport).toHaveBeenLastCalledWith(
      'analysis-1',
      'ar',
    )
    await waitFor(() =>
      expect(reportsApi.listReportLibrary).toHaveBeenCalledTimes(2),
    )
  })

  it('downloads only through the protected report endpoint helper', async () => {
    vi.mocked(reportsApi.listReportLibrary).mockResolvedValue(page([item()]))
    renderReports()

    fireEvent.click(await screen.findByRole('button', { name: 'Download PDF' }))
    await waitFor(() =>
      expect(analysesApi.downloadReportFile).toHaveBeenCalledWith('report-1'),
    )
    expect(analysesApi.downloadBlob).toHaveBeenCalledWith(
      expect.any(Blob),
      'report-en-report-1.pdf',
    )
  })

  it('applies search, filters, sort, reset, and pagination through bounded API queries', async () => {
    vi.mocked(reportsApi.listReportLibrary).mockResolvedValue(
      page([item()], { total: 13, total_pages: 2 }),
    )
    renderReports()
    await screen.findByText('report-1')

    fireEvent.change(screen.getByLabelText('Search reports'), {
      target: { value: 'CPIT-450' },
    })
    fireEvent.change(screen.getByLabelText('Report status'), {
      target: { value: 'available' },
    })
    fireEvent.change(screen.getByLabelText('Exam type'), {
      target: { value: 'Midterm' },
    })
    fireEvent.change(
      screen.getAllByLabelText('Report language', { selector: 'select' })[0],
      { target: { value: 'en' } },
    )
    fireEvent.change(screen.getByLabelText('Sort reports'), {
      target: { value: 'score' },
    })

    await waitFor(() =>
      expect(reportsApi.listReportLibrary).toHaveBeenLastCalledWith(
        expect.objectContaining({
          q: 'CPIT-450',
          status: 'available',
          exam_type: 'Midterm',
          language: 'en',
          sort: 'score',
          page: 1,
          page_size: 12,
        }),
      ),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() =>
      expect(reportsApi.listReportLibrary).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 2, page_size: 12 }),
      ),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Reset filters' }))
    await waitFor(() =>
      expect(reportsApi.listReportLibrary).toHaveBeenLastCalledWith(
        expect.objectContaining({
          q: undefined,
          status: undefined,
          exam_type: undefined,
          language: undefined,
          sort: 'newest',
          page: 1,
        }),
      ),
    )
  })

  it('shows empty, no-results, and retryable load-error states', async () => {
    vi.mocked(reportsApi.listReportLibrary)
      .mockRejectedValueOnce(new Error('Reports temporarily unavailable.'))
      .mockResolvedValue(page())

    const { unmount } = renderReports()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load reports.',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(
      await screen.findByRole('heading', { name: 'No reports available yet' }),
    )
      .toBeInTheDocument()
    expect(
      screen.getByText('Complete an analysis before generating its report.'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Start New Analysis' }),
    ).toHaveAttribute('href', '/analyses/new')
    expect(
      screen.getAllByRole('link', { name: 'View incomplete analyses' }),
    ).toHaveLength(2)
    expect(
      screen.getAllByRole('link', { name: 'View incomplete analyses' })[1],
    ).toHaveAttribute('href', '/analyses')
    unmount()

    vi.mocked(reportsApi.listReportLibrary).mockResolvedValue(page())
    renderReports()
    fireEvent.change(screen.getByLabelText('Search reports'), {
      target: { value: 'missing' },
    })
    expect(
      await screen.findByText('No reports match your search or filters.'),
    ).toBeInTheDocument()
  })

  it('renders natural Arabic labels and RTL without missing-key fallback', async () => {
    window.localStorage.setItem('exam-quality-analyzer-locale', 'ar')
    vi.mocked(reportsApi.listReportLibrary).mockResolvedValue(
      page([
        item(),
        item({
          status: 'not_generated',
          analysis: {
            ...ANALYSIS,
            id: 'analysis-2',
            course_code: 'CPIT-451',
          },
          report: null,
        }),
      ]),
    )

    const { container } = renderReports()
    expect(
      await screen.findByRole('heading', { level: 1, name: 'التقارير' }),
    ).toBeInTheDocument()
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    expect(screen.getByLabelText('البحث في التقارير')).toBeInTheDocument()
    expect(
      container.querySelector('[data-report-status="available"]'),
    ).toHaveTextContent('متاح')
    expect(
      container.querySelector('[data-report-status="not_generated"]'),
    ).toHaveTextContent('لم يتم إنشاء التقرير')
    expect(screen.getAllByRole('link', { name: 'عرض التحليل' })).toHaveLength(2)
    expect(
      screen.getByRole('link', { name: 'عرض التحليلات غير المكتملة' }),
    ).toHaveAttribute('href', '/analyses')
    expect(container).not.toHaveTextContent('تعذر عرض النص المترجم.')
  })

  it('renders the approved Arabic empty-state copy and actions', async () => {
    window.localStorage.setItem('exam-quality-analyzer-locale', 'ar')
    vi.mocked(reportsApi.listReportLibrary).mockResolvedValue(page())

    renderReports()

    expect(
      await screen.findByRole('heading', {
        name: 'لا توجد تقارير متاحة حتى الآن',
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('أكمل التحليل أولًا حتى تتمكن من إنشاء التقرير.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'بدء تحليل جديد' })).toHaveAttribute(
      'href',
      '/analyses/new',
    )
    expect(
      screen.getAllByRole('link', { name: 'عرض التحليلات غير المكتملة' }),
    ).toHaveLength(2)
  })
})
