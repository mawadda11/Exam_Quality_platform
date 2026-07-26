import type { ButtonHTMLAttributes, ReactNode } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  isLoading?: boolean
  loadingLabel?: string
  children: ReactNode
}

export function Button({
  variant = 'primary',
  isLoading = false,
  loadingLabel = 'Loading…',
  className = '',
  disabled,
  children,
  type = 'button',
  ...props
}: ButtonProps) {
  const classes = ['ui-button', `ui-button--${variant}`, className].filter(Boolean).join(' ')

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      {...props}
    >
      {isLoading && <span className="ui-button-spinner" aria-hidden="true" />}
      {isLoading ? loadingLabel : children}
    </button>
  )
}
