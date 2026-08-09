/** One shared outline-icon set (stroke-based, same visual weight as
 * SidebarIcon) reused across toolbars, status badges, and page actions so
 * the whole app draws from a single consistent icon vocabulary rather than
 * each feature inventing its own glyphs. Icons are supplemental: status
 * meaning must never depend on the icon alone, so callers always pair an
 * icon with visible text and treat the icon itself as aria-hidden unless
 * it is the sole content of an actionable control (in which case the
 * caller supplies an accessible name on the control, not the icon). */
export type IconName =
  | 'check-circle'
  | 'alert-circle'
  | 'x-circle'
  | 'question-circle'
  | 'minus-circle'
  | 'search'
  | 'filter'
  | 'close'
  | 'chevron-down'
  | 'chevron-right'
  | 'print'
  | 'download'
  | 'plus'
  | 'arrow-right'
  | 'grid'
  | 'eye'
  | 'trash'

interface IconProps {
  name: IconName
  className?: string
}

export function Icon({ name, className = '' }: IconProps) {
  return (
    <svg
      className={['ui-icon', className].filter(Boolean).join(' ')}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      {name === 'check-circle' && (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M8 12.5l2.5 2.5L16 9.5" />
        </>
      )}
      {name === 'alert-circle' && (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7.5v6" />
          <path d="M12 16.5h.01" />
        </>
      )}
      {name === 'x-circle' && (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M9.5 9.5l5 5M14.5 9.5l-5 5" />
        </>
      )}
      {name === 'question-circle' && (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M9.75 9.5a2.25 2.25 0 1 1 3.4 1.94c-.7.42-1.15.86-1.15 1.81" />
          <path d="M12 16.5h.01" />
        </>
      )}
      {name === 'minus-circle' && (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M8 12h8" />
        </>
      )}
      {name === 'search' && (
        <>
          <circle cx="10.5" cy="10.5" r="6.5" />
          <path d="M19 19l-4.3-4.3" />
        </>
      )}
      {name === 'filter' && <path d="M4 5.5h16L14 13v6l-4 2v-8z" />}
      {name === 'close' && <path d="M6 6l12 12M18 6L6 18" />}
      {name === 'chevron-down' && <path d="M6 9.5l6 6 6-6" />}
      {name === 'chevron-right' && <path d="M9.5 6l6 6-6 6" />}
      {name === 'print' && (
        <>
          <path d="M7 8.5V4h10v4.5" />
          <rect x="4.5" y="8.5" width="15" height="7.5" rx="1.25" />
          <path d="M7 15v4.5h10V15" />
        </>
      )}
      {name === 'download' && (
        <>
          <path d="M12 4.5v10.5M8 11.5l4 4 4-4" />
          <path d="M5 18.5h14" />
        </>
      )}
      {name === 'plus' && <path d="M12 5v14M5 12h14" />}
      {name === 'arrow-right' && <path d="M5 12h14M13 6l6 6-6 6" />}
      {name === 'eye' && (
        <>
          <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
          <circle cx="12" cy="12" r="2.5" />
        </>
      )}
      {name === 'trash' && (
        <>
          <path d="M4.5 7h15" />
          <path d="M9 7V4.5h6V7" />
          <path d="M7 7l.75 12h8.5L17 7" />
          <path d="M10 10.5v5M14 10.5v5" />
        </>
      )}
      {name === 'grid' && (
        <>
          <rect x="4" y="4" width="7" height="7" rx="1" />
          <rect x="13" y="4" width="7" height="7" rx="1" />
          <rect x="4" y="13" width="7" height="7" rx="1" />
          <rect x="13" y="13" width="7" height="7" rx="1" />
        </>
      )}
    </svg>
  )
}
