import type { ReactNode } from 'react'

export type PageStateKind = 'loading' | 'empty' | 'error' | 'success'

interface PageStateProps {
  state: PageStateKind
  title: string
  message?: string
  action?: ReactNode
}

export function PageState({ state, title, message, action }: PageStateProps) {
  const role = state === 'error' ? 'alert' : 'status'

  return (
    <section
      className={`ui-page-state ui-page-state--${state}`}
      role={role}
      aria-busy={state === 'loading' || undefined}
    >
      <h2 className="ui-page-state-title">{title}</h2>
      {message && <p className="ui-page-state-message">{message}</p>}
      {action}
    </section>
  )
}
