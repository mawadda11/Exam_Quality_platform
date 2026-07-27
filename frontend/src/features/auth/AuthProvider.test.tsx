import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as authApi from '../../api/auth'
import { getStoredAccessToken, setStoredAccessToken } from '../../api/authToken'
import type { AuthSessionResponse, FacultyUserResponse } from '../../types/api'
import { AuthProvider, useAuth } from './AuthProvider'

vi.mock('../../api/auth')

const USER: FacultyUserResponse = {
  id: 'user-1',
  email: 'faculty@university.edu',
  display_name: 'Dr Faculty',
  institution: 'Example University',
  department: 'Computing',
  user_type: 'Faculty Member',
  email_verified: false,
  created_at: '2026-01-01T00:00:00Z',
}

const SESSION: AuthSessionResponse = {
  access_token: 'new-access-token',
  token_type: 'bearer',
  expires_in: 3600,
  user: USER,
}

function Probe() {
  const auth = useAuth()
  return (
    <div>
      <output aria-label="auth status">{auth.status}</output>
      <output aria-label="auth email">{auth.user?.email ?? 'none'}</output>
      <button
        type="button"
        onClick={() => void auth.login({ email: USER.email, password: 'StrongPassword2026' })}
      >
        Login
      </button>
      <button type="button" onClick={() => void auth.logout()}>
        Logout
      </button>
    </div>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  window.localStorage.clear()
})

describe('AuthProvider', () => {
  it('restores a stored session through the current-user endpoint', async () => {
    setStoredAccessToken('stored-access-token')
    vi.mocked(authApi.getCurrentFaculty).mockResolvedValue(USER)

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    expect(screen.getByLabelText('auth status')).toHaveTextContent('loading')
    expect(await screen.findByText(USER.email)).toBeInTheDocument()
    expect(screen.getByLabelText('auth status')).toHaveTextContent('authenticated')
  })

  it('clears an invalid stored session', async () => {
    setStoredAccessToken('expired-access-token')
    vi.mocked(authApi.getCurrentFaculty).mockRejectedValue(new Error('expired'))

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    await waitFor(() => expect(screen.getByLabelText('auth status')).toHaveTextContent('anonymous'))
    expect(getStoredAccessToken()).toBe('')
  })

  it('stores a successful login session and revokes it on logout', async () => {
    vi.mocked(authApi.loginFaculty).mockResolvedValue(SESSION)
    vi.mocked(authApi.logoutFaculty).mockResolvedValue(undefined)

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Login' }))
    expect(await screen.findByText(USER.email)).toBeInTheDocument()
    expect(getStoredAccessToken()).toBe('new-access-token')

    fireEvent.click(screen.getByRole('button', { name: 'Logout' }))
    await waitFor(() => expect(screen.getByLabelText('auth status')).toHaveTextContent('anonymous'))
    expect(authApi.logoutFaculty).toHaveBeenCalledTimes(1)
    expect(getStoredAccessToken()).toBe('')
  })
})
