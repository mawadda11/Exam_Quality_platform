import { useId, type ReactNode } from 'react'

interface ResponsiveTableProps {
  caption: string
  children: ReactNode
  className?: string
  captionVisible?: boolean
}

export function ResponsiveTable({
  caption,
  children,
  className = '',
  captionVisible = false,
}: ResponsiveTableProps) {
  const captionId = useId()

  return (
    <div
      className="ui-responsive-table"
      role="region"
      aria-labelledby={captionId}
      tabIndex={0}
    >
      <table className={className}>
        <caption id={captionId} className={captionVisible ? undefined : 'visually-hidden'}>
          {caption}
        </caption>
        {children}
      </table>
    </div>
  )
}
