import { useEffect, useRef, type KeyboardEvent, type ReactNode, type RefObject } from 'react'
import { useI18n } from '../../i18n/I18nProvider'
import { Icon } from './Icon'

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

interface DrawerProps {
  isOpen: boolean
  onClose: () => void
  titleId: string
  title: ReactNode
  meta?: ReactNode
  children: ReactNode
  /** Focus returns here when the drawer closes. Callers pass the ref of the
   * control that opened the drawer (e.g. a table row's "View details"
   * button) so keyboard users land back where they started. */
  returnFocusRef?: RefObject<HTMLElement | null>
  className?: string
  /** Identifies the current content instance (e.g. a question id). The
   * drawer body's scroll position is reset to the top whenever this changes
   * or the drawer opens, since the underlying body element stays mounted
   * across different selections instead of remounting. */
  scrollKey?: string
}

/** One shared accessible side drawer, reused for every drawer/dialog-style
 * overlay in the results UI (question details, CLO/topic mapping details)
 * instead of each page inventing its own overlay. Mirrors the focus-trap
 * pattern already used by MobileNavigation. Positioned with logical
 * properties, so it opens from the trailing edge in both LTR and RTL
 * without direction-specific styling. */
export function Drawer({
  isOpen,
  onClose,
  titleId,
  title,
  meta,
  children,
  returnFocusRef,
  className = '',
  scrollKey,
}: DrawerProps) {
  const { t } = useI18n()
  const drawerRef = useRef<HTMLDivElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return
    if (bodyRef.current) bodyRef.current.scrollTop = 0
  }, [isOpen, scrollKey])

  useEffect(() => {
    if (!isOpen) return undefined
    const firstControl = drawerRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)
    firstControl?.focus()
    const elementToRefocus = returnFocusRef?.current

    function handleEscape(event: globalThis.KeyboardEvent): void {
      if (event.key !== 'Escape') return
      event.preventDefault()
      onClose()
    }

    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
      window.requestAnimationFrame(() => elementToRefocus?.focus())
    }
  }, [isOpen, onClose, returnFocusRef])

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
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

  if (!isOpen) return null

  return (
    <>
      <button
        type="button"
        className="ui-drawer-backdrop"
        aria-label={t('Close')}
        onClick={onClose}
      />
      <div
        ref={drawerRef}
        className={['ui-drawer', className].filter(Boolean).join(' ')}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={handleKeyDown}
      >
        <div className="ui-drawer-header">
          <div className="ui-drawer-heading-copy">
            <h2 id={titleId} className="ui-drawer-title">
              {title}
            </h2>
            {meta && <div className="ui-drawer-meta">{meta}</div>}
          </div>
          <button
            type="button"
            className="ui-drawer-close"
            aria-label={t('Close')}
            onClick={onClose}
          >
            <Icon name="close" />
          </button>
        </div>
        <div ref={bodyRef} className="ui-drawer-body">
          {children}
        </div>
      </div>
    </>
  )
}
