import type { HTMLAttributes } from 'react'

type BrandMarkSize = 'small' | 'medium' | 'large'

interface BrandMarkProps extends HTMLAttributes<HTMLDivElement> {
  size?: BrandMarkSize
  showName?: boolean
}

export function BrandMark({
  size = 'medium',
  showName = true,
  className = '',
  ...props
}: BrandMarkProps) {
  const classes = ['ui-brand-mark', `ui-brand-mark--${size}`, className]
    .filter(Boolean)
    .join(' ')

  return (
    <div
      className={classes}
      aria-label={showName ? undefined : 'AI Exam Quality Platform'}
      {...props}
    >
      <span className="ui-brand-mark-icon" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 2.75 19 5.5v5.75c0 4.4-2.7 8.1-7 10-4.3-1.9-7-5.6-7-10V5.5l7-2.75Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="m9 12 2 2 4-4"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      {showName && (
        <span className="ui-brand-mark-copy">
          <span className="ui-brand-mark-name">AI Exam Quality</span>
          <span className="ui-brand-mark-subtitle">Platform</span>
        </span>
      )}
    </div>
  )
}
