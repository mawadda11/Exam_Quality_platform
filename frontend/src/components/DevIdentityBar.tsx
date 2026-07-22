import { useState, type ChangeEvent } from 'react'
import { getStoredDevUserEmail, setStoredDevUserEmail } from '../api/identity'

export function DevIdentityBar() {
  const [email, setEmail] = useState<string>(() => getStoredDevUserEmail())

  function handleChange(event: ChangeEvent<HTMLInputElement>): void {
    const value = event.target.value
    setEmail(value)
    setStoredDevUserEmail(value)
  }

  return (
    <div className="dev-identity-bar" role="note">
      <label>
        <span>Development identity (temporary, not real sign-in)</span>
        <input
          type="email"
          value={email}
          onChange={handleChange}
          placeholder="you@institution.edu"
          aria-label="Development identity email"
        />
      </label>
    </div>
  )
}
