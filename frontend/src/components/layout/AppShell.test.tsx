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
    expect(screen.getByRole('link', { name: 'Reports' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'New Analysis' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Methodology & Help' })).toBeInTheDocument()
    for (const label of ['Dashboard', 'Analyses', 'Reports', 'Methodology & Help']) {
      const link = screen.getByRole('link', { name: label })
      expect(link.querySelector('.sidebar-navigation-icon')).toHaveAttribute(
        'aria-hidden',
        'true',
      )
    }
    expect(
      screen
        .getByRole('link', { name: 'New Analysis' })
        .querySelector('.sidebar-navigation-icon'),
    ).toHaveAttribute('aria-hidden', 'true')
    expect(screen.getByRole('heading', { name: 'Dashboard content' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveAttribute(
      'href',
      '#main-content',
    )
    expect(screen.getByRole('main')).toHaveAttribute('tabindex', '-1')
  })

  it('does not expose the removed development identity control', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<h1>Dashboard content</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByText(/development identity/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/development identity/i)).not.toBeInTheDocument()
  })
})
