import { useI18n } from '../../i18n/I18nProvider'
import type { SemanticConfidenceLevel } from '../../types/api'

const CONFIDENCE_EXPLANATION_KEYS: Record<SemanticConfidenceLevel, string> = {
  High: 'All required governed evidence conditions were satisfied.',
  Medium: 'The governed evidence was usable but included a bounded limitation or mixed result.',
  Low: 'Required evidence was missing or insufficient; the academic status must be Not Verified.',
}

interface SemanticConfidenceBadgeProps {
  level: SemanticConfidenceLevel
}

export function SemanticConfidenceBadge({ level }: SemanticConfidenceBadgeProps) {
  const { t } = useI18n()
  return (
    <span
      className={`semantic-confidence-badge semantic-confidence-badge--${level.toLowerCase()}`}
      title={`${t(CONFIDENCE_EXPLANATION_KEYS[level])} ${t('This category is not a score, severity, priority, or probability.')}`}
      data-semantic-confidence={level}
    >
      {t('Semantic confidence')}: {t(level)}
    </span>
  )
}
