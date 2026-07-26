import { Card } from '../../components/ui/Card'
import type { AnalysisResponse } from '../../types/api'
import { calculateAnalysisMetrics } from './analysisMetrics'

interface AnalysisSummaryCardsProps {
  analyses: AnalysisResponse[]
}

export function AnalysisSummaryCards({ analyses }: AnalysisSummaryCardsProps) {
  const metrics = calculateAnalysisMetrics(analyses)

  return (
    <section className="analysis-summary-grid" aria-label="Analysis summary">
      <Card as="article" className="analysis-summary-card">
        <h2>Total analyses</h2>
        <p>{metrics.total}</p>
      </Card>
      <Card as="article" className="analysis-summary-card">
        <h2>Completed analyses</h2>
        <p>{metrics.completed}</p>
      </Card>
      <Card as="article" className="analysis-summary-card">
        <h2>Linked reanalyses</h2>
        <p>{metrics.linkedReanalyses}</p>
      </Card>
    </section>
  )
}
