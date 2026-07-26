import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { MobileNavigation } from './MobileNavigation'

function renderNavigation() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <MobileNavigation />
    </MemoryRouter>,
  )
}

describe('MobileNavigation', () => {
  it('opens an accessible keyboard-operable navigation drawer', () => {
    renderNavigation()

    fireEvent.click(screen.getByRole('button', { name: /open navigation/i }))

    expect(screen.getByRole('dialog', { name: /application navigation/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getAllByRole('button', { name: /close navigation/i }).at(-1)).toHaveFocus()
  })

  it('closes on Escape and returns focus to its trigger', async () => {
    renderNavigation()
    const trigger = screen.getByRole('button', { name: /open navigation/i })
    fireEvent.click(trigger)

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('keeps keyboard focus within the open modal drawer', () => {
    renderNavigation()
    fireEvent.click(screen.getByRole('button', { name: /open navigation/i }))
    const closeButton = screen.getAllByRole('button', { name: /close navigation/i }).at(-1)
    closeButton?.focus()

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Tab', shiftKey: true })

    expect(screen.getByRole('link', { name: 'New Analysis' })).toHaveFocus()
  })
})
