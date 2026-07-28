import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useOptionalAuth } from '../../features/auth/AuthProvider'
import { useI18n } from '../../i18n/I18nProvider'

export function UserAccountPanel() {
  const { t } = useI18n()
  const auth = useOptionalAuth()
  const navigate = useNavigate()
  const [isSigningOut, setIsSigningOut] = useState(false)

  const user = auth?.user
  if (!auth || !user) return null
  const currentAuth = auth

  async function handleLogout(): Promise<void> {
    setIsSigningOut(true)
    await currentAuth.logout()
    navigate('/login', { replace: true })
  }

  return (
    <section className="user-account-panel" aria-label={t('Faculty Member')}>
      <div className="user-account-avatar" aria-hidden="true">
        {user.display_name.slice(0, 1).toUpperCase()}
      </div>
      <div className="user-account-copy">
        <strong>{user.display_name}</strong>
        <span>{user.email}</span>
      </div>
      <button
        type="button"
        className="user-account-logout"
        disabled={isSigningOut}
        onClick={() => void handleLogout()}
      >
        {isSigningOut ? t('Signing out…') : t('Sign out')}
      </button>
    </section>
  )
}
