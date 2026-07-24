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
  const isAiAssisted = finding.evaluator_type === 'semantic_ai'

  return (
    <li className="finding-card">
      <div className="finding-card-header">
        <strong>{finding.requirement_name}</strong>
        <div className="finding-card-badges">
          {isAiAssisted && <span className="ai-assisted-tag">AI-Assisted</span>}
          <StatusBadge status={finding.status} />
        </div>
      </div>
      <p className="finding-card-meta">
        {finding.dimension} · <GovernanceTag sourceType={finding.source_type} />
      </p>
      {isAiAssisted && (
        <p className="finding-ai-meta">
          Confidence: {Math.round(finding.confidence * 100)}%
          {finding.ai_provider && ` · Provider: ${finding.ai_provider}`}
          {finding.ai_model && ` · Model: ${finding.ai_model}`}
          {finding.prompt_template_version && ` · Prompt: ${finding.prompt_template_version}`}
          {finding.kb_version && ` · KB: ${finding.kb_version}`}
        </p>
      )}
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
