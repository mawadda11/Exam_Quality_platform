import { Card } from '../../components/ui/Card'
import { Icon, type IconName } from '../../components/ui/Icon'
import { useI18n } from '../../i18n/I18nProvider'
import type { AnalysisResponse } from '../../types/api'
import { calculateAnalysisMetrics } from './analysisMetrics'
import type { ReportsAvailableState } from './useReportsAvailableCount'

interface SummaryCardProps {
  icon: IconName
  value: number | string
  label: string
  isBusy?: boolean
}

function SummaryCard({ icon, value, label, isBusy = false }: SummaryCardProps) {
  return (
    <Card as="article" className="analysis-summary-card">
      <span className="analysis-summary-card-icon" aria-hidden="true">
        <Icon name={icon} />
      </span>
      <strong aria-busy={isBusy || undefined}>{value}</strong>
      <h2>{label}</h2>
    </Card>
  )
}

interface AnalysisSummaryCardsProps {
  analyses: AnalysisResponse[]
  reportsAvailable: ReportsAvailableState
}

export function AnalysisSummaryCards({ analyses, reportsAvailable }: AnalysisSummaryCardsProps) {
  const { t } = useI18n()
  const metrics = calculateAnalysisMetrics(analyses)
  const reportsValue =
    reportsAvailable.status === 'ready' ? reportsAvailable.count : '—'

  return (
    <section className="analysis-summary-grid" aria-label={t('Analysis summary')}>
      <SummaryCard icon="grid" value={metrics.total} label={t('Total analyses')} />
      <SummaryCard
        icon="check-circle"
        value={metrics.completed}
        label={t('Completed analyses')}
      />
      <SummaryCard
        icon="alert-circle"
        value={metrics.needsAttention}
        label={t('Analyses needing attention')}
      />
      <SummaryCard
        icon="download"
        value={reportsValue}
        label={t('Reports available')}
        isBusy={reportsAvailable.status === 'loading'}
      />
    </section>
  )
}
