import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { ReportResponse } from '../../types/api'
import { ReportSection } from './ReportSection'

vi.mock('../../api/analyses')

function report(overrides: Partial<ReportResponse> = {}): ReportResponse {
  return {
    id: 'report-1',
    analysis_id: 'analysis-1',
    format: 'pdf',
    language: 'en',
    kb_version: '1.0',
    score: '75.00',
    score_label: null,
    denominator: 2,
    satisfied_count: 1,
    partially_satisfied_count: 1,
    not_satisfied_count: 0,
    not_verified_count: 0,
    not_applicable_count: 0,
    size_bytes: 1024,
    created_at: '2026-07-24T12:00:00Z',
    ...overrides,
  }
}

function renderSection(
  reports: React.ComponentProps<typeof ReportSection>['reports'] = {
    status: 'ready',
    data: [],
  },
  onRefreshReports = vi.fn().mockResolvedValue([]),
) {
  const onRetryReports = vi.fn()
  render(
    <ReportSection
      analysisId="analysis-1"
      reports={reports}
      onRetryReports={onRetryReports}
      onRefreshReports={onRefreshReports}
    />,
  )
  return { onRetryReports, onRefreshReports }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ReportSection', () => {
  it('keeps Generate Report usable when report history failed', () => {
    const { onRetryReports } = renderSection({
      status: 'error',
      message: 'Report history unavailable.',
    })

    expect(screen.getByRole('button', { name: /generate report/i })).toBeEnabled()
    expect(screen.getByText(/report history unavailable/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /retry report history/i }))
    expect(onRetryReports).toHaveBeenCalled()
  })

  it('generates for the current analysis and refreshes only report history', async () => {
    vi.mocked(analysesApi.generateReport).mockResolvedValue(report())
    const onRefreshReports = vi.fn().mockResolvedValue([report()])
    renderSection({ status: 'ready', data: [] }, onRefreshReports)

    fireEvent.click(screen.getByRole('button', { name: /generate report/i }))

    await vi.waitFor(() => expect(onRefreshReports).toHaveBeenCalledTimes(1))
    expect(await screen.findByText(/report history was refreshed/i))
      .toBeInTheDocument()
    expect(analysesApi.generateReport).toHaveBeenCalledWith('analysis-1', 'en')
    expect(analysesApi.listReports).not.toHaveBeenCalled()
  })

  it('generates an Arabic report when Arabic is selected', async () => {
    vi.mocked(analysesApi.generateReport).mockResolvedValue(report({ language: 'ar' }))
    renderSection()

    fireEvent.change(screen.getByLabelText(/report language/i), { target: { value: 'ar' } })
    fireEvent.click(screen.getByRole('button', { name: /generate report/i }))

    await vi.waitFor(() =>
      expect(analysesApi.generateReport).toHaveBeenCalledWith('analysis-1', 'ar'),
    )
  })

  it('shows generation and history-refresh failures distinctly', async () => {
    vi.mocked(analysesApi.generateReport).mockResolvedValue(report())
    renderSection(
      { status: 'ready', data: [] },
      vi.fn().mockRejectedValue(new ApiError(503, 'History unavailable.')),
    )

    fireEvent.click(screen.getByRole('button', { name: /generate report/i }))
    expect(await screen.findByText(/report was generated, but report history/i))
      .toBeInTheDocument()
  })

  it('downloads an analysis-scoped report', async () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' })
    vi.mocked(analysesApi.downloadReportFile).mockResolvedValue(blob)
    renderSection({ status: 'ready', data: [report()] })

    fireEvent.click(screen.getByRole('button', { name: /download pdf/i }))

    await vi.waitFor(() =>
      expect(analysesApi.downloadReportFile).toHaveBeenCalledWith('report-1'),
    )
    expect(analysesApi.downloadBlob).toHaveBeenCalledWith(
      blob,
      'report-en-report-1.pdf',
    )
  })

  it('shows Insufficient Evidence from an existing report record', () => {
    renderSection({
      status: 'ready',
      data: [report({ score: null, score_label: 'Insufficient Evidence' })],
    })
    expect(screen.getByText(/insufficient evidence/i)).toBeInTheDocument()
  })
})
