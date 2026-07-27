import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ApiError } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { useAuth } from '../../features/auth/AuthProvider'

export function RegisterRoute() {
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
      setError('Passwords do not match.')
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
      setError(caught instanceof ApiError ? caught.detail : 'Account creation failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card as="section" variant="raised" className="auth-card auth-card--wide">
      <div className="auth-card-heading">
        <p className="auth-eyebrow">Faculty registration</p>
        <h1>Create your account</h1>
        <p>Each faculty member receives a private dashboard and analysis history.</p>
      </div>

      {error && (
        <Alert variant="error" title="Could not create account">
          <p>{error}</p>
        </Alert>
      )}

      <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
        <div className="auth-form-grid">
          <label className="auth-field">
            <span>Full name</span>
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
            <span>Email address</span>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="auth-field">
            <span>Institution <small>optional</small></span>
            <input
              type="text"
              autoComplete="organization"
              maxLength={200}
              value={institution}
              onChange={(event) => setInstitution(event.target.value)}
            />
          </label>
          <label className="auth-field">
            <span>Department <small>optional</small></span>
            <input
              type="text"
              maxLength={200}
              value={department}
              onChange={(event) => setDepartment(event.target.value)}
            />
          </label>
          <label className="auth-field">
            <span>Password</span>
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
            <span>Confirm password</span>
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
          Use at least 12 characters with at least one letter and one number.
        </p>
        <Button type="submit" isLoading={submitting} loadingLabel="Creating account…">
          Create account
        </Button>
      </form>

      <p className="auth-switch">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </Card>
  )
}
