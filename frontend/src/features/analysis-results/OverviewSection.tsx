import { Card } from '../../components/ui/Card'
import { ScoreRing } from '../../components/ui/ScoreRing'
import { StatusBadge } from '../../components/ui/StatusBadge'
import type {
  AcademicStatus,
  AnalysisResponse,
  AnalysisScoreResponse,
  RuleCoverageAuditResponse,
} from '../../types/api'
import { ReanalysisAction } from './ReanalysisAction'
import { RuleCoveragePanel } from './RuleCoveragePanel'
import type { ResultResource } from './useAnalysisResultsData'

interface OverviewSectionProps {
  analysis: AnalysisResponse
  score: AnalysisScoreResponse
  ruleCoverage: ResultResource<RuleCoverageAuditResponse>
  onRetryRuleCoverage: () => void
  onReanalysisCreated?: (reanalysis: AnalysisResponse) => void
}

function statusCounts(score: AnalysisScoreResponse): [AcademicStatus, number][] {
  return [
    ['Satisfied', score.satisfied_count],
    ['Partially Satisfied', score.partially_satisfied_count],
    ['Not Satisfied', score.not_satisfied_count],
    ['Not Verified', score.not_verified_count],
    ['Not Applicable', score.not_applicable_count],
  ]
}

export function OverviewSection({
  analysis,
  score,
  ruleCoverage,
  onRetryRuleCoverage,
  onReanalysisCreated,
}: OverviewSectionProps) {
  return (
    <div className="overview-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>Overview</h2>
          <p>A summary of the quality checks completed for this exam.</p>
        </div>
      </div>

      <div className="overview-score-layout">
        <Card as="section" className="overview-score-card">
          <ScoreRing
            score={score.score}
            denominator={score.denominator}
            emptyLabel={score.label ?? 'Insufficient Evidence'}
          />
        </Card>

        <Card as="section" className="overview-status-card">
          <h3>Evaluation results</h3>
          <ul className="status-count-grid">
            {statusCounts(score).map(([status, count]) => (
              <li key={status}>
                <strong>{count}</strong>
                <StatusBadge status={status} />
              </li>
            ))}
          </ul>
          <div className="score-transparency">
            <h4>About this score</h4>
            <p>
              This score summarizes the checks the platform was able to verify for this exam.
            </p>
            <p className="results-supporting-text">
              Results that could not be verified or did not apply remain visible, but they do not
              lower the score. Checks planned for a future release are also excluded.
            </p>
          </div>
        </Card>
      </div>

      <RuleCoveragePanel coverage={ruleCoverage} onRetry={onRetryRuleCoverage} />

      {onReanalysisCreated && (
        <ReanalysisAction analysisId={analysis.id} onCreated={onReanalysisCreated} />
      )}
    </div>
  )
}
