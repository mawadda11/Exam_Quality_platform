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
  const earnedCredits = score.satisfied_count + score.partially_satisfied_count * 0.5
  return (
    <div className="overview-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>Overview</h2>
          <p>Backend score and approved academic-status distribution.</p>
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
          <h3>Academic-status counts</h3>
          <ul className="status-count-grid">
            {statusCounts(score).map(([status, count]) => (
              <li key={status}>
                <strong>{count}</strong>
                <StatusBadge status={status} />
              </li>
            ))}
          </ul>
          <div className="score-transparency">
            <h4>Score denominator transparency</h4>
            <p>
              Earned credit: {score.satisfied_count} × 1.0 +{' '}
              {score.partially_satisfied_count} × 0.5 + {score.not_satisfied_count} × 0.0 ={' '}
              <strong>{earnedCredits.toFixed(1)}</strong>.
            </p>
            <p className="results-supporting-text">
              The denominator contains {score.denominator} verified applicable{' '}
              {score.denominator === 1 ? 'rule' : 'rules'}. Not Verified and Not Applicable
              remain visible but are excluded from scoring. Semantic confidence does not change
              rule weight.
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
