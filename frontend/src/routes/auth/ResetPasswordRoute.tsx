import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { confirmPasswordReset } from '../../api/auth'
import { ApiError } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'

export function ResetPasswordRoute() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setError(null)
    if (!token) {
      setError('This reset link is missing its security token.')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await confirmPasswordReset({ token, new_password: password })
      navigate('/login', { replace: true, state: { passwordReset: true } })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Could not reset your password.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card as="section" variant="raised" className="auth-card">
      <div className="auth-card-heading">
        <p className="auth-eyebrow">Account recovery</p>
        <h1>Choose a new password</h1>
        <p>The link is single-use and expires after the configured reset period.</p>
      </div>

      {!token && (
        <Alert variant="warning" title="Invalid reset link">
          <p>Request a new password reset link before continuing.</p>
        </Alert>
      )}
      {error && (
        <Alert variant="error" title="Could not reset password">
          <p>{error}</p>
        </Alert>
      )}

      <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
        <label className="auth-field">
          <span>New password</span>
          <input
            type="password"
            autoComplete="new-password"
            minLength={12}
            maxLength={128}
            required
            disabled={!token}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <label className="auth-field">
          <span>Confirm new password</span>
          <input
            type="password"
            autoComplete="new-password"
            minLength={12}
            maxLength={128}
            required
            disabled={!token}
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
        </label>
        <p className="auth-guidance">Use at least 12 characters with a letter and a number.</p>
        <Button
          type="submit"
          disabled={!token}
          isLoading={submitting}
          loadingLabel="Updating password…"
        >
          Update password
        </Button>
      </form>

      <p className="auth-switch">
        <Link to="/forgot-password">Request a new reset link</Link>
      </p>
    </Card>
  )
}
