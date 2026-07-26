import { Link } from 'react-router-dom'
import { routeForAnalysis } from '../../router/analysisRouting'
import type { AnalysisResponse } from '../../types/api'

interface AnalysisHistoryListProps {
  analyses: AnalysisResponse[]
}

/** FR-017 "Store analysis history": GET /analyses already returns every
 * analysis this user owns, most recent first - this is the first UI to
 * actually surface it, so a completed analysis (and any reanalyses linked
 * to it) can be found again rather than only being reachable right after
 * it finishes processing. */
export function AnalysisHistoryList({ analyses }: AnalysisHistoryListProps) {
  return (
    <div className="analysis-history">
      <h2>Your Analyses</h2>
      <ul className="analysis-history-list">
        {analyses.map((analysis) => (
          <li key={analysis.id}>
            <Link to={routeForAnalysis(analysis)}>
              <strong>
                <bdi>{analysis.course.code}</bdi> — {analysis.exam_type} ({analysis.term})
              </strong>
              <span className="analysis-history-meta">
                {analysis.state}
                {analysis.predecessor_analysis_id && ' · reanalysis'}
                {' · '}
                {new Date(analysis.created_at).toLocaleDateString()}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
