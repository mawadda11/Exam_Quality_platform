import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { PageState } from '../../components/ui/PageState'
import { useAuth } from './AuthProvider'

export function ProtectedRoute() {
  const auth = useAuth()
  const location = useLocation()

  if (auth.status === 'loading') {
    return (
      <main className="auth-loading" id="main-content">
        <PageState state="loading" title="Checking your session" message="Please wait…" />
      </main>
    )
  }

  if (auth.status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
