import { Card } from '../../components/ui/Card'
import { useI18n } from '../../i18n/I18nProvider'
import type { AnalysisResponse } from '../../types/api'
import { calculateAnalysisMetrics } from './analysisMetrics'

export function AnalysisSummaryCards({ analyses }: { analyses: AnalysisResponse[] }) {
  const { t } = useI18n()
  const metrics = calculateAnalysisMetrics(analyses)
  return (
    <section className="analysis-summary-grid" aria-label={t('Analysis summary')}>
      <Card as="article">
        <h2>{t('Total analyses')}</h2>
        <strong>{metrics.total}</strong>
      </Card>
      <Card as="article">
        <h2>{t('Completed analyses')}</h2>
        <strong>{metrics.completed}</strong>
      </Card>
      <Card as="article">
        <h2>{t('Linked reanalyses')}</h2>
        <strong>{metrics.linkedReanalyses}</strong>
      </Card>
    </section>
  )
}
