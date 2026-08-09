import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
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

  if (coverage.status === 'loading') return null

  if (coverage.status === 'error') {
    return (
      <Alert
        variant="error"
        title={t('Could not confirm analysis completion')}
      >
        <p>{coverage.message}</p>
        <Button variant="secondary" onClick={onRetry}>
          {t('Retry completion check')}
        </Button>
      </Alert>
    )
  }

  if (!coverage.data.runtime_integrity_ok) {
    return (
      <Alert variant="error" title={t('Analysis execution needs attention')}>
        <p>
          {t(
            'Supported checks did not complete. This is a system execution issue, not an academic result.',
            { count: coverage.data.not_run_rules },
          )}
        </p>
      </Alert>
    )
  }

  if (coverage.data.conditional_capability_gap_rules > 0) {
    return (
      <p className="overview-limited-check-note">
        {t(
          'Some supported checks could not be fully evaluated. This does not count as an exam failure.',
          { count: coverage.data.conditional_capability_gap_rules },
        )}
      </p>
    )
  }

  return null
}
