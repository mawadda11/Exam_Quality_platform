import type { FindingResponse, RecommendationResponse } from '../../types/api'
import { EvidenceDrillDown, type EvidenceLookupKind } from './EvidenceDrillDown'
import type { EvidenceLookups } from './lookups'
import { SemanticConfidenceBadge } from './SemanticConfidenceBadge'
import { SemanticEvaluationDetails } from './SemanticEvaluationDetails'
import { GovernanceTag, StatusBadge } from './StatusBadge'

interface FindingCardProps {
  finding: FindingResponse
  lookups: EvidenceLookups
  recommendations?: RecommendationResponse[]
  unavailableLookups?: ReadonlySet<EvidenceLookupKind>
}

export function FindingCard({
  finding,
  lookups,
  recommendations = [],
  unavailableLookups,
}: FindingCardProps) {
  const isAiAssisted = finding.evaluator_type === 'semantic_ai'
  const hasAiProvenance =
    isAiAssisted &&
    Boolean(
      finding.ai_provider ||
        finding.ai_model ||
        finding.prompt_template_version ||
        finding.kb_version,
    )

  return (
    <li className="finding-card">
      <div className="finding-card-header">
        <strong>{finding.requirement_name}</strong>
        <div className="finding-card-badges">
          {isAiAssisted && <span className="ai-assisted-tag">AI-Assisted</span>}
          {finding.confidence_level && (
            <SemanticConfidenceBadge level={finding.confidence_level} />
          )}
          <StatusBadge status={finding.status} />
        </div>
      </div>
      <p className="finding-card-meta">
        {finding.dimension} · Requirement <bdi>{finding.requirement_id}</bdi> · Rule{' '}
        <bdi>{finding.rule_id}</bdi> · <GovernanceTag sourceType={finding.source_type} />
      </p>
      {hasAiProvenance && (
        <p className="finding-ai-meta">
          {finding.ai_provider && (
            <>
              Provider: <bdi>{finding.ai_provider}</bdi>
            </>
          )}
          {finding.ai_model && (
            <>
              {' '}
              · Model: <bdi>{finding.ai_model}</bdi>
            </>
          )}
          {finding.prompt_template_version && (
            <>
              {' '}
              · Prompt: <bdi>{finding.prompt_template_version}</bdi>
            </>
          )}
          {finding.kb_version && (
            <>
              {' '}
              · KB: <bdi>{finding.kb_version}</bdi>
            </>
          )}
        </p>
      )}
      <p dir="auto">{finding.explanation}</p>
      {finding.evaluation_details && (
        <details className="semantic-evaluation-disclosure">
          <summary>Semantic evaluation details</summary>
          <SemanticEvaluationDetails finding={finding} />
        </details>
      )}
      <details>
        <summary>Evidence ({finding.evidence.length})</summary>
        <EvidenceDrillDown
          evidence={finding.evidence}
          status={finding.status}
          lookups={lookups}
          unavailableLookups={unavailableLookups}
        />
      </details>
      {recommendations.length > 0 && (
        <ul className="recommendation-list">
          {recommendations.map((rec) => (
            <li key={rec.recommendation_id}>
              <strong>{rec.title}</strong>
              <p dir="auto">{rec.text}</p>
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
