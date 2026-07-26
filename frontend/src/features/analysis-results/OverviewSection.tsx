import { Card } from '../../components/ui/Card'
import { ScoreRing } from '../../components/ui/ScoreRing'
import { StatusBadge } from '../../components/ui/StatusBadge'
import type {
  AcademicStatus,
  AnalysisResponse,
  AnalysisScoreResponse,
} from '../../types/api'
import { ReanalysisAction } from './ReanalysisAction'

interface OverviewSectionProps {
  analysis: AnalysisResponse
  score: AnalysisScoreResponse
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
  onReanalysisCreated,
}: OverviewSectionProps) {
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
          <p className="results-supporting-text">
            The score denominator contains {score.denominator} verified applicable{' '}
            {score.denominator === 1 ? 'rule' : 'rules'}. Not Verified and Not Applicable
            remain visible but are excluded from scoring.
          </p>
        </Card>
      </div>

      {onReanalysisCreated && (
        <ReanalysisAction analysisId={analysis.id} onCreated={onReanalysisCreated} />
      )}
    </div>
  )
}
