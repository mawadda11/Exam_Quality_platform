import type { SemanticConfidenceLevel } from '../../types/api'

const CONFIDENCE_EXPLANATIONS: Record<SemanticConfidenceLevel, string> = {
  High: 'All required governed evidence conditions were satisfied.',
  Medium: 'The governed evidence was usable but included a bounded limitation or mixed result.',
  Low: 'Required evidence was missing or insufficient; the academic status must be Not Verified.',
}

interface SemanticConfidenceBadgeProps {
  level: SemanticConfidenceLevel
}

export function SemanticConfidenceBadge({ level }: SemanticConfidenceBadgeProps) {
  return (
    <span
      className={`semantic-confidence-badge semantic-confidence-badge--${level.toLowerCase()}`}
      title={`${CONFIDENCE_EXPLANATIONS[level]} This category is not a score, severity, priority, or probability.`}
      data-semantic-confidence={level}
    >
      Semantic confidence: {level}
    </span>
  )
}
