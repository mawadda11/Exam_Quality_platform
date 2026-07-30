import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../api/analyses'
import * as authApi from '../api/auth'
import { setStoredAccessToken } from '../api/authToken'
import { AuthProvider } from '../features/auth/AuthProvider'
import type { AuthSessionResponse, FacultyUserResponse } from '../types/api'
import { AppRoutes } from './AppRoutes'

vi.mock('../api/analyses')
vi.mock('../api/auth')

const USER: FacultyUserResponse = {
  id: 'user-1',
  email: 'faculty@university.edu',
  display_name: 'Dr Faculty',
  institution: null,
  department: null,
  user_type: 'Faculty Member',
  preferred_language: 'en',
  email_verified: false,
  created_at: '2026-01-01T00:00:00Z',
}

const SESSION: AuthSessionResponse = {
  access_token: 'signed-access-token',
  token_type: 'bearer',
  expires_in: 3600,
  user: USER,
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  window.localStorage.clear()
  vi.mocked(analysesApi.listAnalyses).mockResolvedValue([])
})

describe('authentication routes', () => {
  it('redirects an anonymous faculty member from the dashboard to sign in', async () => {
    renderAt('/dashboard')
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('redirects an anonymous faculty member from reports to sign in', async () => {
    renderAt('/reports')
    expect(await screen.findByRole('heading', { name: 'Sign in' }))
      .toBeInTheDocument()
  })

  it('signs in and opens the private dashboard', async () => {
    vi.mocked(authApi.loginFaculty).mockResolvedValue(SESSION)
    renderAt('/login')

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: USER.email },
    })
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'StrongPassword2026' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByText(USER.email)).toBeInTheDocument()
  })

  it('shows the generic password-reset response and development link', async () => {
    vi.mocked(authApi.requestPasswordReset).mockResolvedValue({
      message: 'If an active account matches that email, password reset instructions were sent.',
      debug_reset_token: 'debug-reset-token-value-that-is-long-enough',
    })
    renderAt('/forgot-password')

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: USER.email },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send reset instructions' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Request received')
    expect(
      screen.getByRole('link', { name: 'choose a new password' }).getAttribute('href'),
    ).toContain('/reset-password?token=')
  })

  it('restores a stored session before rendering protected content', async () => {
    setStoredAccessToken('stored-token')
    vi.mocked(authApi.getCurrentFaculty).mockResolvedValue(USER)
    renderAt('/dashboard')

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument(),
    )
    expect(authApi.getCurrentFaculty).toHaveBeenCalledTimes(1)
  })
})
