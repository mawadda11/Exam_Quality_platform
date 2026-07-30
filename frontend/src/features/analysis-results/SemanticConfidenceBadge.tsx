import { useI18n } from '../../i18n/I18nProvider'
import type { SemanticConfidenceLevel } from '../../types/api'

const CONFIDENCE_EXPLANATION_KEYS: Record<SemanticConfidenceLevel, string> = {
  High: 'The linked evidence was complete and clear for this judgment.',
  Medium: 'The linked evidence was usable but included a limitation or mixed support.',
  Low: 'The linked evidence was missing or insufficient for a reliable judgment.',
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
      {t('Evidence reliability')}: {t(level)}
    </span>
  )
}
