import type { CSSProperties } from 'react'
import { useI18n } from '../../i18n/I18nProvider'

interface ScoreRingProps {
  score: number | string | null
  denominator: number
  label?: string
  emptyLabel?: string
  denominatorKind?: 'verified' | 'applicable'
}

function numericScore(score: number | string): number {
  const parsed = typeof score === 'number' ? score : Number.parseFloat(score)
  if (!Number.isFinite(parsed)) return 0
  return Math.min(100, Math.max(0, parsed))
}

export function ScoreRing({
  score,
  denominator,
  label,
  emptyLabel,
  denominatorKind = 'verified',
}: ScoreRingProps) {
  const { t } = useI18n()
  const translatedLabel = label ?? t('Overall Exam Quality Score')
  const translatedEmptyLabel = emptyLabel ?? t('Insufficient Evidence')
  const empty = score === null
  const scoreText = empty ? translatedEmptyLabel : `${score}%`
  const denominatorText =
    denominatorKind === 'applicable'
      ? denominator === 0
        ? t('No applicable checks were available')
        : denominator === 1
          ? t('Based on 1 applicable check')
          : t('Based on {count} applicable checks', { count: denominator })
      : denominator === 0
        ? t('No verified checks were available')
        : denominator === 1
          ? t('Based on 1 verified check')
          : t('Based on {count} verified checks', { count: denominator })
  const angle = empty ? 0 : numericScore(score) * 3.6
  const style = { '--score-angle': `${angle}deg` } as CSSProperties

  return (
    <div
      className={`ui-score-ring${empty ? ' ui-score-ring--empty' : ''}`}
      role="img"
      aria-label={`${translatedLabel}: ${scoreText}. ${denominatorText}.`}
    >
      <div className="ui-score-ring-graphic" style={style} aria-hidden="true">
        <span className="ui-score-ring-value">{scoreText}</span>
      </div>
      <p className="ui-score-ring-label">{translatedLabel}</p>
      <p className="ui-score-ring-denominator">{denominatorText}</p>
    </div>
  )
}
