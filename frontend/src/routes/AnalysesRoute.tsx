import { Link } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { PageHeader } from '../components/ui/PageHeader'
import { PageState } from '../components/ui/PageState'
import { AnalysisHistoryTable } from '../features/analysis-history/AnalysisHistoryTable'
import { useAnalyses } from '../features/analysis-history/useAnalyses'
import { useI18n } from '../i18n/I18nProvider'

export function AnalysesRoute() {
  const { t } = useI18n()
  const state = useAnalyses()

  return (
    <div className="route-stack route-content-wide">
      <PageHeader
        title={t('Analyses')}
        description={t('Open an existing analysis or begin a new one.')}
        actions={
          <Link className="ui-button" to="/analyses/new">
            {t('New Analysis')}
          </Link>
        }
      />
      {state.status === 'loading' && (
        <PageState state="loading" title={t('Loading analyses')} message={t('Retrieving your analyses…')} />
      )}
      {state.status === 'error' && (
        <PageState
          state="error"
          title={t('Could not load analyses')}
          message={state.message}
          action={
            <Button variant="secondary" onClick={state.retry}>
              {t('Retry analyses')}
            </Button>
          }
        />
      )}
      {state.status === 'ready' && state.analyses.length === 0 && (
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
      {state.status === 'ready' && state.analyses.length > 0 && (
        <AnalysisHistoryTable analyses={state.analyses} caption={t('All analyses')} />
      )}
    </div>
  )
}
