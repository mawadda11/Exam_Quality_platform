export type SidebarIconName =
  | 'dashboard'
  | 'analyses'
  | 'reports'
  | 'methodology'
  | 'new-analysis'

interface SidebarIconProps {
  name: SidebarIconName
}

export function SidebarIcon({ name }: SidebarIconProps) {
  return (
    <svg
      className="sidebar-navigation-icon"
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      {name === 'dashboard' && (
        <>
          <rect x="4" y="4" width="6" height="6" rx="1" />
          <rect x="14" y="4" width="6" height="6" rx="1" />
          <rect x="4" y="14" width="6" height="6" rx="1" />
          <rect x="14" y="14" width="6" height="6" rx="1" />
        </>
      )}
      {name === 'analyses' && (
        <>
          <path d="M8 4.5h7.5L19 8v11.5H8z" />
          <path d="M15.5 4.5V8H19M5 8v11.5h10.5M10.5 12h6M10.5 15h6" />
        </>
      )}
      {name === 'reports' && (
        <>
          <path d="M7 3.75h7l3 3V20.25H7z" />
          <path d="M14 3.75v3h3M9.5 11h5M9.5 14h5M9.5 17h3.5" />
        </>
      )}
      {name === 'methodology' && (
        <>
          <path d="M4 5.5c2.75-.8 5.4-.35 8 1.35v12c-2.6-1.7-5.25-2.15-8-1.35z" />
          <path d="M20 5.5c-2.75-.8-5.4-.35-8 1.35v12c2.6-1.7 5.25-2.15 8-1.35z" />
        </>
      )}
      {name === 'new-analysis' && <path d="M12 5v14M5 12h14" />}
    </svg>
  )
}
