import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  description?: string
  eyebrow?: string
  actions?: ReactNode
  headingLevel?: 1 | 2 | 3
}

export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
  headingLevel = 1,
}: PageHeaderProps) {
  const Heading = `h${headingLevel}` as const

  return (
    <header className="ui-page-header">
      <div className="ui-page-header-copy">
        {eyebrow && <p className="ui-page-header-eyebrow">{eyebrow}</p>}
        <Heading className="ui-page-header-title">{title}</Heading>
        {description && <p className="ui-page-header-description">{description}</p>}
      </div>
      {actions && <div className="ui-page-header-actions">{actions}</div>}
    </header>
  )
}
