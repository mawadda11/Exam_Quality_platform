import type { AnalysisResponse, AnalysisScoreResponse } from '../../types/api'
import { ReanalysisAction } from './ReanalysisAction'

interface OverviewSectionProps {
  analysis: AnalysisResponse
  score: AnalysisScoreResponse
  onReanalysisCreated?: (reanalysis: AnalysisResponse) => void
}

export function OverviewSection({ analysis, score, onReanalysisCreated }: OverviewSectionProps) {
  return (
    <div className="overview-section">
      <h3>Overview</h3>
      <p>
        {analysis.course.code} — {analysis.exam_type} ({analysis.term})
      </p>
      {analysis.predecessor_analysis_id && (
        <p className="notice">
          This is a reanalysis linked to a previous analysis - the earlier results and any of its
          reports remain unchanged and available.
        </p>
      )}

      <div className="score-panel">
        {score.score !== null ? (
          <p className="overall-score">
            Overall Exam Quality Score: <strong>{score.score}</strong>
            <span className="score-denominator">
              {' '}
              (based on {score.denominator} verified applicable rule
              {score.denominator === 1 ? '' : 's'})
            </span>
          </p>
        ) : (
          <p className="overall-score overall-score-insufficient" role="status">
            {score.label ?? 'Insufficient Evidence'}
          </p>
        )}

        <ul className="status-counts">
          <li>Satisfied: {score.satisfied_count}</li>
          <li>Partially Satisfied: {score.partially_satisfied_count}</li>
          <li>Not Satisfied: {score.not_satisfied_count}</li>
          <li>Not Verified: {score.not_verified_count}</li>
          <li>Not Applicable: {score.not_applicable_count}</li>
        </ul>
      </div>

      {onReanalysisCreated && (
        <ReanalysisAction analysisId={analysis.id} onCreated={onReanalysisCreated} />
      )}
    </div>
  )
}
