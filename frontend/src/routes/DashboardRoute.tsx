import { Link } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { PageHeader } from '../components/ui/PageHeader'
import { PageState } from '../components/ui/PageState'
import { AnalysisHistoryTable } from '../features/analysis-history/AnalysisHistoryTable'
import { AnalysisSummaryCards } from '../features/analysis-history/AnalysisSummaryCards'
import { calculateAnalysisMetrics } from '../features/analysis-history/analysisMetrics'
import { useAnalyses } from '../features/analysis-history/useAnalyses'
import { useI18n } from '../i18n/I18nProvider'

export function DashboardRoute() {
  const { t } = useI18n()
  const state = useAnalyses()
  const metrics =
    state.status === 'ready' ? calculateAnalysisMetrics(state.analyses) : null

  return (
    <div className="route-stack route-content-wide">
      <PageHeader
        eyebrow={t('Academic quality support')}
        title={t('Dashboard')}
        description={t('Create a new evidence-based exam analysis or return to an existing analysis.')}
        actions={
          <Link className="ui-button" to="/analyses/new">
            {t('New Analysis')}
          </Link>
        }
      />

      {state.status === 'loading' && (
        <PageState state="loading" title={t('Loading dashboard')} message={t('Retrieving your analyses…')} />
      )}
      {state.status === 'error' && (
        <PageState
          state="error"
          title={t('Could not load dashboard')}
          message={state.message}
          action={
            <Button variant="secondary" onClick={state.retry}>
              {t('Retry dashboard')}
            </Button>
          }
        />
      )}
      {state.status === 'ready' && (
        <>
          <AnalysisSummaryCards analyses={state.analyses} />
          {metrics && metrics.recent.length > 0 ? (
            <section className="dashboard-recent">
              <div className="dashboard-section-heading">
                <h2>{t('Recent analyses')}</h2>
                <Link to="/analyses">{t('View all analyses')}</Link>
              </div>
              <AnalysisHistoryTable
                analyses={metrics.recent}
                caption={t('Recent analyses')}
              />
            </section>
          ) : (
            <PageState
              state="empty"
              title={t('No analyses yet')}
              message={t('Create an analysis to upload an exam and its Course Specification.')}
              action={
                <Link className="ui-button" to="/analyses/new">
                  {t('New Analysis')}
                </Link>
              }
            />
          )}
        </>
      )}
    </div>
  )
}
