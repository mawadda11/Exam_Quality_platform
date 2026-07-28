import { useState } from 'react'
import {
  downloadBlob,
  downloadReportFile,
  generateReport,
} from '../../api/analyses'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import type { ReportLanguage, ReportResponse } from '../../types/api'
import type { ResultResource } from './useAnalysisResultsData'

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
  const { locale, t, formatDateTime } = useI18n()
  const [reportLanguage, setReportLanguage] = useState<ReportLanguage>(locale)
  const [isGenerating, setIsGenerating] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  function scoreSummary(report: ReportResponse): string {
    if (report.score !== null) {
      return `${report.score}% (${report.denominator})`
    }
    return t(report.score_label ?? 'Insufficient Evidence')
  }

  async function handleGenerate(): Promise<void> {
    setIsGenerating(true)
    setError(null)
    setSuccessMessage(null)
    try {
      await generateReport(analysisId, reportLanguage)
    } catch (generateError) {
      setError(localizeInterfaceError(generateError, locale, t, 'Could not generate the report.'))
      setIsGenerating(false)
      return
    }

    try {
      await onRefreshReports()
      setSuccessMessage(t('The report was generated and report history was refreshed.'))
    } catch {
      setError(t('The report was generated, but report history could not be refreshed. Retry the history request.'))
    } finally {
      setIsGenerating(false)
    }
  }

  async function handleDownload(report: ReportResponse): Promise<void> {
    setDownloadingId(report.id)
    setError(null)
    try {
      const blob = await downloadReportFile(report.id)
      downloadBlob(blob, `report-${report.language}-${report.id}.pdf`)
    } catch (downloadError) {
      setError(localizeInterfaceError(downloadError, locale, t, 'Could not download the report.'))
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <div className="report-section results-section-stack">
      <div className="results-section-heading report-section-heading">
        <div>
          <h2>{t('Report')}</h2>
          <p>
            {t('Generate and download report snapshots for analysis')} <bdi>{analysisId}</bdi>.
          </p>
        </div>
        <div className="report-generation-controls">
          <label>
            <span>{t('Report language')}</span>
            <select
              value={reportLanguage}
              onChange={(event) => setReportLanguage(event.target.value as ReportLanguage)}
            >
              <option value="ar">{locale === 'ar' ? 'العربية' : 'Arabic'}</option>
              <option value="en">{locale === 'ar' ? 'الإنجليزية' : 'English'}</option>
            </select>
          </label>
          <Button
            onClick={() => void handleGenerate()}
            isLoading={isGenerating}
            loadingLabel={t('Generating…')}
          >
            {t('Generate Report')}
          </Button>
        </div>
      </div>

      <Alert variant="info" title={t('Report language')}>
        {t('Report narrative and governed presentation wording use the selected language. Original source wording and evidence remain available for audit.')}
      </Alert>

      {error && (
        <Alert variant="error" title={t('Report action could not be completed')}>
          {error}
        </Alert>
      )}
      {successMessage && (
        <Alert variant="success" title={t('Report generated')}>
          {successMessage}
        </Alert>
      )}

      {reports.status === 'loading' && (
        <div className="results-resource-state" role="status" aria-busy="true">
          {t('Loading report history…')}
        </div>
      )}
      {reports.status === 'error' && (
        <Alert variant="error" title={t('Report history could not be loaded')}>
          <p>{reports.message}</p>
          <Button variant="secondary" onClick={onRetryReports}>
            {t('Retry report history')}
          </Button>
        </Alert>
      )}
      {reports.status === 'ready' && reports.data.length === 0 && (
        <p className="results-empty-state">{t('No reports have been generated yet.')}</p>
      )}
      {reports.status === 'ready' && reports.data.length > 0 && (
        <ul className="report-list">
          {reports.data.map((report) => (
            <li key={report.id}>
              <Card as="article" className="report-list-item">
                <div>
                  <strong>
                    <time dateTime={report.created_at}>{formatDateTime(report.created_at)}</time>
                  </strong>
                  <p className="report-list-meta">
                    {scoreSummary(report)} · {t('Report language')}: {report.language === 'ar' ? (locale === 'ar' ? 'العربية' : 'Arabic') : (locale === 'ar' ? 'الإنجليزية' : 'English')} · {t('KB version')} <bdi>{report.kb_version}</bdi>
                  </p>
                </div>
                <Button
                  variant="secondary"
                  onClick={() => void handleDownload(report)}
                  isLoading={downloadingId === report.id}
                  loadingLabel={t('Downloading…')}
                >
                  {t('Download PDF')}
                </Button>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
