import type { FindingResponse, RecommendationResponse } from '../../types/api'
import { EvidenceDrillDown } from './EvidenceDrillDown'
import type { EvidenceLookups } from './lookups'
import { GovernanceTag, StatusBadge } from './StatusBadge'

interface FindingCardProps {
  finding: FindingResponse
  lookups: EvidenceLookups
  recommendations?: RecommendationResponse[]
}

export function FindingCard({ finding, lookups, recommendations = [] }: FindingCardProps) {
  return (
    <li className="finding-card">
      <div className="finding-card-header">
        <strong>{finding.requirement_name}</strong>
        <StatusBadge status={finding.status} />
      </div>
      <p className="finding-card-meta">
        {finding.dimension} · <GovernanceTag sourceType={finding.source_type} />
      </p>
      <p>{finding.explanation}</p>
      <details>
        <summary>Evidence ({finding.evidence.length})</summary>
        <EvidenceDrillDown evidence={finding.evidence} status={finding.status} lookups={lookups} />
      </details>
      {recommendations.length > 0 && (
        <ul className="recommendation-list">
          {recommendations.map((rec) => (
            <li key={rec.recommendation_id}>
              <strong>{rec.title}</strong>
              <p>{rec.text}</p>
              <span className="recommendation-meta">
                {rec.recommendation_type} · For: {rec.target_user}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}
