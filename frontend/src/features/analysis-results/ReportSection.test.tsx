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

beforeEach(() => {
  vi.mocked(analysesApi.generateReport).mockReset()
  vi.mocked(analysesApi.listReports).mockReset()
  vi.mocked(analysesApi.downloadReportFile).mockReset()
  vi.mocked(analysesApi.downloadBlob).mockReset()
})

describe('ReportSection', () => {
  it('shows an honest empty state when no reports exist yet', () => {
    render(<ReportSection analysisId="analysis-1" initialReports={[]} />)
    expect(screen.getByText(/no reports have been generated yet/i)).toBeInTheDocument()
  })

  it('shows the reports passed in immediately, without waiting on a network call', () => {
    render(<ReportSection analysisId="analysis-1" initialReports={[report()]} />)
    expect(screen.getByText(/75\.00/)).toBeInTheDocument()
    expect(screen.getByText(/kb version 1\.0/i)).toBeInTheDocument()
  })

  it('generates a report and refreshes the list to include it', async () => {
    vi.mocked(analysesApi.generateReport).mockResolvedValue(report({ id: 'report-new' }))
    vi.mocked(analysesApi.listReports).mockResolvedValue([report({ id: 'report-new' })])

    render(<ReportSection analysisId="analysis-1" initialReports={[]} />)
    fireEvent.click(screen.getByRole('button', { name: /generate report/i }))

    expect(await screen.findByText(/75\.00/)).toBeInTheDocument()
    expect(analysesApi.generateReport).toHaveBeenCalledWith('analysis-1')
    expect(analysesApi.listReports).toHaveBeenCalledWith('analysis-1')
  })

  it('shows an error message when report generation fails', async () => {
    vi.mocked(analysesApi.generateReport).mockRejectedValue(
      new ApiError(409, 'A report can only be generated for a completed analysis.'),
    )

    render(<ReportSection analysisId="analysis-1" initialReports={[]} />)
    fireEvent.click(screen.getByRole('button', { name: /generate report/i }))

    expect(await screen.findByText(/can only be generated for a completed analysis/i)).toBeInTheDocument()
  })

  it('downloads a report by fetching the blob and triggering a save', async () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' })
    vi.mocked(analysesApi.downloadReportFile).mockResolvedValue(blob)

    render(<ReportSection analysisId="analysis-1" initialReports={[report()]} />)
    fireEvent.click(screen.getByRole('button', { name: /download/i }))

    await vi.waitFor(() => {
      expect(analysesApi.downloadReportFile).toHaveBeenCalledWith('report-1')
    })
    expect(analysesApi.downloadBlob).toHaveBeenCalledWith(blob, 'report-report-1.pdf')
  })

  it('shows an error message when the download fails', async () => {
    vi.mocked(analysesApi.downloadReportFile).mockRejectedValue(
      new ApiError(404, 'Report not found.'),
    )

    render(<ReportSection analysisId="analysis-1" initialReports={[report()]} />)
    fireEvent.click(screen.getByRole('button', { name: /download/i }))

    expect(await screen.findByText(/report not found/i)).toBeInTheDocument()
  })

  it('shows Insufficient Evidence for a report with no numeric score', () => {
    render(
      <ReportSection
        analysisId="analysis-1"
        initialReports={[report({ score: null, score_label: 'Insufficient Evidence' })]}
      />,
    )
    expect(screen.getByText(/insufficient evidence/i)).toBeInTheDocument()
  })
})
