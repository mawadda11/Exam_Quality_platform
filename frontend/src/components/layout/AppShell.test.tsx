import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AppShell } from './AppShell'

describe('AppShell', () => {
  it('renders the approved navigation and marks the current route', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<h1>Dashboard content</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('link', { name: 'Analyses' })).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('link', { name: 'New Analysis' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'What We Evaluate' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Dashboard content' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveAttribute(
      'href',
      '#main-content',
    )
    expect(screen.getByRole('main')).toHaveAttribute('tabindex', '-1')
  })

  it('keeps the temporary development identity explicit without auth controls', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<h1>Dashboard content</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText(/development identity \(temporary, not real sign-in\)/i))
      .toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /sign out/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /profile/i })).not.toBeInTheDocument()
  })
})
