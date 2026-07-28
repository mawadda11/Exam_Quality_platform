import type { ReactNode } from 'react'
import { useI18n } from '../../i18n/I18nProvider'

interface OriginalTextDisclosureProps {
  children: ReactNode
  className?: string
}

export function OriginalTextDisclosure({
  children,
  className = '',
}: OriginalTextDisclosureProps) {
  const { locale, t } = useI18n()
  if (locale !== 'ar') return null

  return (
    <details className={`original-text-disclosure ${className}`.trim()}>
      <summary>{t('Show original text')}</summary>
      <div className="original-text-disclosure__content" lang="en" dir="ltr">
        {children}
      </div>
    </details>
  )
}
