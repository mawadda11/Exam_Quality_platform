import { useState } from 'react'
import { downloadBlob, downloadReportFile, generateReport, listReports } from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { ReportResponse } from '../../types/api'

function formatGeneratedAt(isoTimestamp: string): string {
  return new Date(isoTimestamp).toLocaleString()
}

function scoreSummary(report: ReportResponse): string {
  if (report.score !== null) {
    const plural = report.denominator === 1 ? '' : 's'
    return `${report.score} (based on ${report.denominator} verified applicable rule${plural})`
  }
  return report.score_label ?? 'Insufficient Evidence'
}

interface ReportSectionProps {
  analysisId: string
  initialReports: ReportResponse[]
}

/** On-demand only (M10 decision): reports are never generated automatically
 * by the processing pipeline - this "Generate Report" action is the only
 * way one is created. Regenerating adds a new report to the list below
 * rather than replacing the previous one (every generation is preserved). */
export function ReportSection({ analysisId, initialReports }: ReportSectionProps) {
  const [reports, setReports] = useState<ReportResponse[]>(initialReports)
  const [isGenerating, setIsGenerating] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleGenerate(): Promise<void> {
    setIsGenerating(true)
    setError(null)
    try {
      await generateReport(analysisId)
      const refreshed = await listReports(analysisId)
      setReports(refreshed)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not generate the report.')
    } finally {
      setIsGenerating(false)
    }
  }

  async function handleDownload(report: ReportResponse): Promise<void> {
    setDownloadingId(report.id)
    setError(null)
    try {
      const blob = await downloadReportFile(report.id)
      downloadBlob(blob, `report-${report.id}.pdf`)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not download the report.')
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <div className="report-section">
      <h3>Report</h3>
      <p>
        Each generated report is a PDF snapshot of the score, findings, evidence, and
        recommendations at the moment it was created.
      </p>

      <button type="button" onClick={() => void handleGenerate()} disabled={isGenerating}>
        {isGenerating ? 'Generating…' : 'Generate Report'}
      </button>

      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}

      {reports.length === 0 ? (
        <p className="notice">No reports have been generated yet.</p>
      ) : (
        <ul className="report-list">
          {reports.map((report) => (
            <li key={report.id} className="report-list-item">
              <div>
                <strong>{formatGeneratedAt(report.created_at)}</strong>
                <p className="report-list-meta">
                  {scoreSummary(report)} · KB version {report.kb_version}
                </p>
              </div>
              <button
                type="button"
                onClick={() => void handleDownload(report)}
                disabled={downloadingId === report.id}
              >
                {downloadingId === report.id ? 'Downloading…' : 'Download'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
