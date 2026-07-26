import { useState } from 'react'
import {
  downloadBlob,
  downloadReportFile,
  generateReport,
} from '../../api/analyses'
import { ApiError } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import type { ReportResponse } from '../../types/api'
import type { ResultResource } from './useAnalysisResultsData'

function formatGeneratedAt(isoTimestamp: string): string {
  return new Date(isoTimestamp).toLocaleString()
}

function scoreSummary(report: ReportResponse): string {
  if (report.score !== null) {
    const plural = report.denominator === 1 ? '' : 's'
    return `${report.score}% (based on ${report.denominator} verified applicable rule${plural})`
  }
  return report.score_label ?? 'Insufficient Evidence'
}

interface ReportSectionProps {
  analysisId: string
  reports: ResultResource<ReportResponse[]>
  onRetryReports: () => void
  onRefreshReports: () => Promise<ReportResponse[]>
}

export function ReportSection({
  analysisId,
  reports,
  onRetryReports,
  onRefreshReports,
}: ReportSectionProps) {
  const [isGenerating, setIsGenerating] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleGenerate(): Promise<void> {
    setIsGenerating(true)
    setError(null)
    try {
      await generateReport(analysisId)
    } catch (generateError) {
      setError(
        generateError instanceof ApiError
          ? generateError.detail
          : 'Could not generate the report.',
      )
      setIsGenerating(false)
      return
    }

    try {
      await onRefreshReports()
    } catch {
      setError(
        'The report was generated, but report history could not be refreshed. Retry the history request.',
      )
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
    } catch (downloadError) {
      setError(
        downloadError instanceof ApiError
          ? downloadError.detail
          : 'Could not download the report.',
      )
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <div className="report-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>Report</h2>
          <p>
            Generate and download report snapshots for analysis <bdi>{analysisId}</bdi>.
          </p>
        </div>
        <Button
          onClick={() => void handleGenerate()}
          isLoading={isGenerating}
          loadingLabel="Generating…"
        >
          Generate Report
        </Button>
      </div>

      {error && (
        <Alert variant="error" title="Report action could not be completed">
          {error}
        </Alert>
      )}

      {reports.status === 'loading' && (
        <div className="results-resource-state" role="status" aria-busy="true">
          Loading report history…
        </div>
      )}
      {reports.status === 'error' && (
        <Alert variant="error" title="Report history could not be loaded">
          <p>
            {reports.message} Generate Report remains available for this analysis.
          </p>
          <Button variant="secondary" onClick={onRetryReports}>
            Retry report history
          </Button>
        </Alert>
      )}
      {reports.status === 'ready' && reports.data.length === 0 && (
        <p className="results-empty-state">No reports have been generated yet.</p>
      )}
      {reports.status === 'ready' && reports.data.length > 0 && (
        <ul className="report-list">
          {reports.data.map((report) => (
            <li key={report.id}>
              <Card as="article" className="report-list-item">
                <div>
                  <strong>
                    <time dateTime={report.created_at}>
                      {formatGeneratedAt(report.created_at)}
                    </time>
                  </strong>
                  <p className="report-list-meta">
                    {scoreSummary(report)} · KB version <bdi>{report.kb_version}</bdi>
                  </p>
                </div>
                <Button
                  variant="secondary"
                  onClick={() => void handleDownload(report)}
                  isLoading={downloadingId === report.id}
                  loadingLabel="Downloading…"
                >
                  Download PDF
                </Button>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
