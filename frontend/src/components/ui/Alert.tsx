import type { HTMLAttributes, ReactNode } from 'react'

export type AlertVariant = 'info' | 'success' | 'warning' | 'error'

const DEFAULT_TITLES: Record<AlertVariant, string> = {
  info: 'Information',
  success: 'Success',
  warning: 'Warning',
  error: 'Error',
}

const ICONS: Record<AlertVariant, string> = {
  info: 'i',
  success: '✓',
  warning: '!',
  error: '×',
}

interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant
  title?: string
  children: ReactNode
}

export function Alert({
  variant = 'info',
  title,
  children,
  className = '',
  ...props
}: AlertProps) {
  const classes = ['ui-alert', `ui-alert--${variant}`, className].filter(Boolean).join(' ')
  const role = variant === 'warning' || variant === 'error' ? 'alert' : 'status'

  return (
    <div className={classes} role={role} {...props}>
      <span className="ui-alert-icon" aria-hidden="true">
        {ICONS[variant]}
      </span>
      <div className="ui-alert-content">
        <strong className="ui-alert-title">{title ?? DEFAULT_TITLES[variant]}</strong>
        {children}
      </div>
    </div>
  )
}
