import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../api/analyses'
import * as reportsApi from '../api/reports'
import { I18nProvider } from '../i18n/I18nProvider'
import type { ReportResponse } from '../types/api'
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
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:protected-report')
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
})

describe('ReportPreviewRoute', () => {
  it('loads owner-safe metadata and PDF content into an accessible preview', async () => {
    renderPreview()

    expect(
      await screen.findByTitle('Report PDF preview'),
    ).toHaveAttribute('src', 'blob:protected-report')
    expect(reportsApi.getReportMetadata).toHaveBeenCalledWith('report-1')
    expect(analysesApi.downloadReportFile).toHaveBeenCalledWith('report-1')
    expect(screen.getByText('English Report')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Reports' }))
      .toHaveAttribute('href', '/reports')

    fireEvent.click(screen.getByRole('button', { name: 'Download PDF' }))
    expect(analysesApi.downloadBlob).toHaveBeenCalledWith(
      expect.any(Blob),
      'report-en-report-1.pdf',
    )
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
    expect(await screen.findByTitle('Report PDF preview')).toBeInTheDocument()
  })
})
