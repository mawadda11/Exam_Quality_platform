import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { downloadBlob, downloadReportFile } from '../api/analyses'
import { getReportMetadata } from '../api/reports'
import { Button } from '../components/ui/Button'
import { PageHeader } from '../components/ui/PageHeader'
import { PageState } from '../components/ui/PageState'
import { useI18n } from '../i18n/I18nProvider'
import { localizeInterfaceError } from '../i18n/localizeError'
import type { ReportResponse } from '../types/api'

type PreviewState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; report: ReportResponse; blob: Blob; url: string }

export function ReportPreviewRoute() {
  const { reportId = '' } = useParams()
  const { locale, t } = useI18n()
  const [reloadToken, setReloadToken] = useState(0)
  const [state, setState] = useState<PreviewState>({ status: 'loading' })

  useEffect(() => {
    let active = true
    let objectUrl: string | null = null
    void Promise.all([
      getReportMetadata(reportId),
      downloadReportFile(reportId),
    ])
      .then(([report, blob]) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setState({ status: 'ready', report, blob, url: objectUrl })
      })
      .catch((error: unknown) => {
        if (!active) return
        setState({
          status: 'error',
          message: localizeInterfaceError(
            error,
            locale,
            t,
            'Could not preview the report.',
          ),
        })
      })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [locale, reloadToken, reportId, t])

  return (
    <div className="route-stack route-content-wide report-preview-route">
      <PageHeader
        title={t('Preview Report')}
        description={
          state.status === 'ready'
            ? t(
                state.report.language === 'ar'
                  ? 'Arabic Report'
                  : 'English Report',
              )
            : t('Review the generated PDF before downloading it.')
        }
        actions={
          <Link className="ui-button ui-button--secondary" to="/reports">
            {t('Back to Reports')}
          </Link>
        }
      />

      {state.status === 'loading' && (
        <PageState
          state="loading"
          title={t('Loading report preview')}
          message={t('Retrieving the protected report…')}
        />
      )}

      {state.status === 'error' && (
        <PageState
          state="error"
          title={t('Report preview could not be loaded')}
          message={state.message}
          action={
            <Button
              variant="secondary"
              onClick={() => {
                setState({ status: 'loading' })
                setReloadToken((current) => current + 1)
              }}
            >
              {t('Retry')}
            </Button>
          }
        />
      )}

      {state.status === 'ready' && (
        <>
          <div className="report-preview-actions">
            <Button
              onClick={() =>
                downloadBlob(
                  state.blob,
                  `report-${state.report.language}-${state.report.id}.pdf`,
                )
              }
            >
              {t('Download PDF')}
            </Button>
          </div>
          <iframe
            className="report-preview-frame"
            src={state.url}
            title={t('Report PDF preview')}
          />
        </>
      )}
    </div>
  )
}
