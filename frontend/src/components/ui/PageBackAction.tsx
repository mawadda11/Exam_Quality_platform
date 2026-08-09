import { useMemo, type MouseEvent } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useI18n } from '../../i18n/I18nProvider'

function explicitBackDestination(pathname: string): string | null {
  if (pathname === '/dashboard') return null
  if (pathname === '/analyses') return '/dashboard'
  if (pathname === '/analyses/new') return '/analyses'
  if (pathname === '/reports') return '/dashboard'
  if (/^\/reports\/[^/]+\/preview$/.test(pathname)) return '/reports'
  if (pathname === '/evaluation-scope') return '/dashboard'

  const analysisRoute = pathname.match(/^\/analyses\/([^/]+)(?:\/([^/]+))?/)
  if (analysisRoute) {
    const [, analysisId, step] = analysisRoute
    if (step === 'start') return `/analyses/${analysisId}/documents`
    return '/analyses'
  }
  return '/dashboard'
}

export function PageBackAction() {
  const location = useLocation()
  const { locale, t } = useI18n()
  const destination = useMemo(
    () => explicitBackDestination(location.pathname),
    [location.pathname],
  )
  if (!destination) return null

  function guardUnsavedReview(event: MouseEvent<HTMLAnchorElement>): void {
    if (document.body.dataset.unsavedExtractionReview !== 'true') return
    if (!window.confirm(t('Discard unsaved extraction review changes?'))) {
      event.preventDefault()
    }
  }

  return (
    <Link
      className="page-back-action"
      to={destination}
      aria-label={t('Back')}
      onClick={guardUnsavedReview}
    >
      <span aria-hidden="true" className="page-back-action__icon">
        {locale === 'ar' ? '→' : '←'}
      </span>
      {t('Back')}
    </Link>
  )
}
