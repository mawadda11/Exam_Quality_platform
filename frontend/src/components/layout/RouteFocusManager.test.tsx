import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { RouteFocusManager } from './RouteFocusManager'

function FocusHarness() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <main id="main-content">
      <RouteFocusManager />
      <h1>{location.pathname}</h1>
      <button type="button" onClick={() => navigate('/analyses')}>
        Open analyses
      </button>
      <button
        type="button"
        onClick={() => navigate('/analyses/analysis-1/results/report')}
      >
        Open report tab
      </button>
    </main>
  )
}

describe('RouteFocusManager', () => {
  it('moves focus to the page heading only after a page-level route change', async () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <FocusHarness />
      </MemoryRouter>,
    )

    const initialHeading = screen.getByRole('heading', { name: '/dashboard' })
    expect(initialHeading).not.toHaveFocus()

    fireEvent.click(screen.getByRole('button', { name: 'Open analyses' }))

    const nextHeading = screen.getByRole('heading', { name: '/analyses' })
    await waitFor(() => expect(nextHeading).toHaveFocus())
    expect(nextHeading).toHaveAttribute('tabindex', '-1')
  })

  it('does not steal focus when only the result tab URL changes', async () => {
    render(
      <MemoryRouter
        initialEntries={['/analyses/analysis-1/results/questions']}
      >
        <FocusHarness />
      </MemoryRouter>,
    )

    const tabControl = screen.getByRole('button', { name: 'Open report tab' })
    tabControl.focus()
    fireEvent.click(tabControl)

    await waitFor(() =>
      expect(
        screen.getByRole('heading', {
          name: '/analyses/analysis-1/results/report',
        }),
      ).toBeInTheDocument(),
    )
    expect(tabControl).toHaveFocus()
  })
})
