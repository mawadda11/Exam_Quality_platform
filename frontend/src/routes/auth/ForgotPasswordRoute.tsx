import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { requestPasswordReset } from '../../api/auth'
import { ApiError } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'

export function ForgotPasswordRoute() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [debugToken, setDebugToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const response = await requestPasswordReset(email)
      setMessage(response.message)
      setDebugToken(response.debug_reset_token)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Could not request a reset link.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card as="section" variant="raised" className="auth-card">
      <div className="auth-card-heading">
        <p className="auth-eyebrow">Account recovery</p>
        <h1>Reset your password</h1>
        <p>Enter your account email. The response does not reveal whether an account exists.</p>
      </div>

      {message && (
        <Alert variant="success" title="Request received">
          <p>{message}</p>
          {debugToken && (
            <p>
              Development reset link:{' '}
              <Link to={`/reset-password?token=${encodeURIComponent(debugToken)}`}>
                choose a new password
              </Link>
            </p>
          )}
        </Alert>
      )}
      {error && (
        <Alert variant="error" title="Could not request reset">
          <p>{error}</p>
        </Alert>
      )}

      <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
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
        <Button type="submit" isLoading={submitting} loadingLabel="Requesting…">
          Send reset instructions
        </Button>
      </form>

      <p className="auth-switch">
        <Link to="/login">Return to sign in</Link>
      </p>
    </Card>
  )
}
