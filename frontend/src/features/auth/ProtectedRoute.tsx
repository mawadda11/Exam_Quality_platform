import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { PageState } from '../../components/ui/PageState'
import { useI18n } from '../../i18n/I18nProvider'
import { useAuth } from './AuthProvider'

export function ProtectedRoute() {
  const auth = useAuth()
  const location = useLocation()
  const { t } = useI18n()

  if (auth.status === 'loading') {
    return (
      <main className="auth-loading" id="main-content">
        <PageState state="loading" title={t('Checking your session')} message={t('Please wait…')} />
      </main>
    )
  }

  if (auth.status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
