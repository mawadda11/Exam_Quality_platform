import type { AnalysisResponse, AnalysisScoreResponse } from '../../types/api'

interface OverviewSectionProps {
  analysis: AnalysisResponse
  score: AnalysisScoreResponse
}

export function OverviewSection({ analysis, score }: OverviewSectionProps) {
  return (
    <div className="overview-section">
      <h3>Overview</h3>
      <p>
        {analysis.course.code} — {analysis.exam_type} ({analysis.term})
      </p>

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
    </div>
  )
}
