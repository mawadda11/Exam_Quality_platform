import type { HTMLAttributes } from 'react'

type CardElement = 'div' | 'section' | 'article'
type CardVariant = 'default' | 'muted' | 'raised'

interface CardProps extends HTMLAttributes<HTMLElement> {
  as?: CardElement
  variant?: CardVariant
}

export function Card({
  as: Component = 'div',
  variant = 'default',
  className = '',
  ...props
}: CardProps) {
  const classes = ['ui-card', `ui-card--${variant}`, className].filter(Boolean).join(' ')
  return <Component className={classes} {...props} />
}
