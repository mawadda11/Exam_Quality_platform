import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { BrandMark } from '../ui/BrandMark'
import { PrimaryNavigation } from './PrimaryNavigation'
import { UserAccountPanel } from './UserAccountPanel'

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'

export function MobileNavigation() {
  const [isOpen, setIsOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const drawerRef = useRef<HTMLDivElement>(null)

  function closeAndReturnFocus(): void {
    setIsOpen(false)
    window.requestAnimationFrame(() => triggerRef.current?.focus())
  }

  useEffect(() => {
    if (!isOpen) return undefined
    const firstControl = drawerRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)
    firstControl?.focus()

    function handleEscape(event: globalThis.KeyboardEvent): void {
      if (event.key !== 'Escape') return
      event.preventDefault()
      closeAndReturnFocus()
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen])

  function handleDrawerKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    if (event.key !== 'Tab') return
    const focusable = Array.from(
      drawerRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR) ?? [],
    )
    if (focusable.length === 0) return

    const first = focusable[0]
    const last = focusable.at(-1)
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last?.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first?.focus()
    }
  }

  return (
    <div className="mobile-navigation">
      <button
        ref={triggerRef}
        type="button"
        className="mobile-navigation-trigger"
        aria-expanded={isOpen}
        aria-controls="mobile-navigation-drawer"
        aria-label="Open navigation"
        onClick={() => setIsOpen(true)}
      >
        <span aria-hidden="true">☰</span>
      </button>

      {isOpen && (
        <>
          <button
            type="button"
            className="mobile-navigation-backdrop"
            aria-label="Close navigation"
            onClick={closeAndReturnFocus}
          />
          <div
            ref={drawerRef}
            id="mobile-navigation-drawer"
            className="mobile-navigation-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Application navigation"
            onKeyDown={handleDrawerKeyDown}
          >
            <div className="mobile-navigation-heading">
              <BrandMark size="small" />
              <button
                type="button"
                className="mobile-navigation-close"
                aria-label="Close navigation"
                onClick={closeAndReturnFocus}
              >
                ×
              </button>
            </div>
            <PrimaryNavigation onNavigate={closeAndReturnFocus} />
            <UserAccountPanel />
          </div>
        </>
      )}
    </div>
  )
}
