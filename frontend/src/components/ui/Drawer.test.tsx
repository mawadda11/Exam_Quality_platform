import { useRef, useState } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { I18nProvider } from '../../i18n/I18nProvider'
import { Drawer } from './Drawer'

beforeEach(() => {
  window.localStorage.setItem('exam-quality-analyzer-locale', 'en')
})

function Harness() {
  const [isOpen, setIsOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  return (
    <>
      <button ref={triggerRef} type="button" onClick={() => setIsOpen(true)}>
        Open drawer
      </button>
      <Drawer
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        titleId="test-drawer-title"
        title="Question Q1"
        meta={<span>Page 1</span>}
        returnFocusRef={triggerRef}
      >
        <a href="#first">First link</a>
        <button type="button">Last button</button>
      </Drawer>
    </>
  )
}

function renderHarness() {
  return render(
    <I18nProvider>
      <Harness />
    </I18nProvider>,
  )
}

describe('Drawer', () => {
  it('opens as an accessible labelled dialog and focuses its first control', () => {
    renderHarness()
    fireEvent.click(screen.getByRole('button', { name: 'Open drawer' }))

    const dialog = screen.getByRole('dialog', { name: 'Question Q1' })
    expect(dialog).toBeInTheDocument()
    expect(screen.getByText('Page 1')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Close' }).at(-1)).toHaveFocus()
  })

  it('closes on Escape and returns focus to the triggering control', async () => {
    renderHarness()
    const trigger = screen.getByRole('button', { name: 'Open drawer' })
    fireEvent.click(trigger)

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('closes when the close button is activated', () => {
    renderHarness()
    fireEvent.click(screen.getByRole('button', { name: 'Open drawer' }))

    fireEvent.click(screen.getAllByRole('button', { name: 'Close' }).at(-1)!)

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('closes when the backdrop is activated', () => {
    renderHarness()
    fireEvent.click(screen.getByRole('button', { name: 'Open drawer' }))

    fireEvent.click(screen.getAllByRole('button', { name: 'Close' })[0])

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('traps Tab focus within the drawer', () => {
    renderHarness()
    fireEvent.click(screen.getByRole('button', { name: 'Open drawer' }))
    const lastButton = screen.getByRole('button', { name: 'Last button' })
    lastButton.focus()

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Tab' })

    expect(screen.getAllByRole('button', { name: 'Close' }).at(-1)).toHaveFocus()
  })
})
