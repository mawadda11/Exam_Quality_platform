import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { useAuth } from '../../features/auth/AuthProvider'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'

interface LoginLocationState {
  from?: string
  passwordReset?: boolean
}

export function LoginRoute() {
  const { locale, t } = useI18n()
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const state = (location.state ?? {}) as LoginLocationState
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (auth.status === 'authenticated') return <Navigate to="/dashboard" replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await auth.login({ email, password })
      navigate(state.from || '/dashboard', { replace: true })
    } catch (caught) {
      setError(localizeInterfaceError(caught, locale, t, 'Could not sign in'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card as="section" variant="raised" className="auth-card">
      <div className="auth-card-heading">
        <p className="auth-eyebrow">{t('Faculty access')}</p>
        <h1>{t('Sign in')}</h1>
        <p>{t('Open your private dashboard and continue your exam-quality analyses.')}</p>
      </div>

      {state.passwordReset && (
        <Alert variant="success" title={t('Password updated')}>
          <p>{t('Sign in using your new password.')}</p>
        </Alert>
      )}
      {error && (
        <Alert variant="error" title={t('Could not sign in')}>
          <p>{error}</p>
        </Alert>
      )}

      <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
        <label className="auth-field">
          <span>{t('Email address')}</span>
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="auth-field">
          <span>{t('Password')}</span>
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <div className="auth-form-links">
          <Link to="/forgot-password">{t('Forgot password?')}</Link>
        </div>
        <Button type="submit" isLoading={submitting} loadingLabel={t('Signing in…')}>
          {t('Sign in')}
        </Button>
      </form>

      <p className="auth-switch">
        {t('New to the platform?')} <Link to="/register">{t('Create a faculty account')}</Link>
      </p>
    </Card>
  )
}
