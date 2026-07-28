import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { useAuth } from '../../features/auth/AuthProvider'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'

export function RegisterRoute() {
  const { locale, t } = useI18n()
  const auth = useAuth()
  const navigate = useNavigate()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [institution, setInstitution] = useState('')
  const [department, setDepartment] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (auth.status === 'authenticated') return <Navigate to="/dashboard" replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setError(null)
    if (password !== confirmPassword) {
      setError(t('Passwords do not match.'))
      return
    }
    setSubmitting(true)
    try {
      await auth.register({
        email,
        password,
        display_name: displayName,
        institution: institution || null,
        department: department || null,
      })
      navigate('/dashboard', { replace: true })
    } catch (caught) {
      setError(localizeInterfaceError(caught, locale, t, 'Could not create account'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card as="section" variant="raised" className="auth-card auth-card--wide">
      <div className="auth-card-heading">
        <p className="auth-eyebrow">{t('Faculty registration')}</p>
        <h1>{t('Create your account')}</h1>
        <p>{t('Each faculty member receives a private dashboard and analysis history.')}</p>
      </div>

      {error && (
        <Alert variant="error" title={t('Could not create account')}>
          <p>{error}</p>
        </Alert>
      )}

      <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
        <div className="auth-form-grid">
          <label className="auth-field">
            <span>{t('Full name')}</span>
            <input
              type="text"
              autoComplete="name"
              minLength={2}
              maxLength={200}
              required
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </label>
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
            <span>{t('Institution')} <small>{t('optional')}</small></span>
            <input
              type="text"
              autoComplete="organization"
              maxLength={200}
              value={institution}
              onChange={(event) => setInstitution(event.target.value)}
            />
          </label>
          <label className="auth-field">
            <span>{t('Department')} <small>{t('optional')}</small></span>
            <input
              type="text"
              maxLength={200}
              value={department}
              onChange={(event) => setDepartment(event.target.value)}
            />
          </label>
          <label className="auth-field">
            <span>{t('Password')}</span>
            <input
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              required
              aria-describedby="password-guidance"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <label className="auth-field">
            <span>{t('Confirm password')}</span>
            <input
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              required
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
            />
          </label>
        </div>
        <p id="password-guidance" className="auth-guidance">
          {t('Use at least 12 characters with at least one letter and one number.')}
        </p>
        <Button type="submit" isLoading={submitting} loadingLabel={t('Creating account…')}>
          {t('Create account')}
        </Button>
      </form>

      <p className="auth-switch">
        {t('Already have an account?')} <Link to="/login">{t('Sign in')}</Link>
      </p>
    </Card>
  )
}
