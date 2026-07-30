import { Link } from 'react-router-dom'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { useI18n } from '../../i18n/I18nProvider'
import type { RuleCoverageAuditResponse } from '../../types/api'
import type { ResultResource } from './useAnalysisResultsData'

interface RuleCoveragePanelProps {
  coverage: ResultResource<RuleCoverageAuditResponse>
  onRetry: () => void
}

export function RuleCoveragePanel({
  coverage,
  onRetry,
}: RuleCoveragePanelProps) {
  const { t } = useI18n()

  function readyMessage(data: RuleCoverageAuditResponse) {
    if (!data.runtime_integrity_ok) {
      return {
        variant: 'error' as const,
        title: t('Analysis execution needs attention'),
        body: t(
          'Supported checks did not complete. This is a system execution issue, not an academic result.',
          { count: data.not_run_rules },
        ),
      }
    }

    if (data.conditional_capability_gap_rules > 0) {
      return {
        variant: 'warning' as const,
        title: t('Analysis completed with a limited check'),
        body: t(
          'Some supported checks could not be fully evaluated. This does not count as an exam failure.',
          {
            count: data.conditional_capability_gap_rules,
          },
        ),
      }
    }

    return {
      variant: 'success' as const,
      title: t('Analysis completed successfully'),
      body: t(
        'All checks supported for this analysis completed successfully.',
      ),
    }
  }

  return (
    <Card
      as="section"
      className="results-content-card rule-coverage-panel"
    >
      <h3>{t('Analysis completion')}</h3>

      {coverage.status === 'loading' && (
        <div
          className="results-resource-state"
          role="status"
          aria-busy="true"
        >
          {t('Checking analysis completion…')}
        </div>
      )}

      {coverage.status === 'error' && (
        <Alert
          variant="error"
          title={t('Could not confirm analysis completion')}
        >
          <p>{coverage.message}</p>

          <Button variant="secondary" onClick={onRetry}>
            {t('Retry completion check')}
          </Button>
        </Alert>
      )}

      {coverage.status === 'ready' &&
        (() => {
          const message = readyMessage(coverage.data)

          return (
            <>
              <Alert
                variant={message.variant}
                title={message.title}
              >
                <p>{message.body}</p>
              </Alert>

              <p className="results-supporting-text rule-coverage-scope-link">
                <Link to="/evaluation-scope">
                  {t('See what the platform evaluates')}
                </Link>
              </p>
            </>
          )
        })()}
    </Card>
  )
}