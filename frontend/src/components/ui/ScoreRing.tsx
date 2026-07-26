import type { CSSProperties } from 'react'

interface ScoreRingProps {
  score: number | string | null
  denominator: number
  label?: string
  emptyLabel?: string
}

function numericScore(score: number | string): number {
  const parsed = typeof score === 'number' ? score : Number.parseFloat(score)
  if (!Number.isFinite(parsed)) return 0
  return Math.min(100, Math.max(0, parsed))
}

export function ScoreRing({
  score,
  denominator,
  label = 'Overall Exam Quality Score',
  emptyLabel = 'Insufficient Evidence',
}: ScoreRingProps) {
  const empty = score === null
  const scoreText = empty ? emptyLabel : `${score}%`
  const denominatorText =
    denominator === 1
      ? 'Based on 1 verified applicable rule'
      : `Based on ${denominator} verified applicable rules`
  const angle = empty ? 0 : numericScore(score) * 3.6
  const style = { '--score-angle': `${angle}deg` } as CSSProperties

  return (
    <div
      className={`ui-score-ring${empty ? ' ui-score-ring--empty' : ''}`}
      role="img"
      aria-label={`${label}: ${scoreText}. ${denominatorText}.`}
    >
      <div className="ui-score-ring-graphic" style={style} aria-hidden="true">
        <span className="ui-score-ring-value">{scoreText}</span>
      </div>
      <p className="ui-score-ring-label">{label}</p>
      <p className="ui-score-ring-denominator">{denominatorText}</p>
    </div>
  )
}
