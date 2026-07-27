import { NavLink } from 'react-router-dom'

const NAVIGATION_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', end: true },
  { to: '/analyses', label: 'Analyses', end: true },
  { to: '/analyses/new', label: 'New Analysis', end: true },
  { to: '/evaluation-scope', label: 'What We Evaluate', end: true },
] as const

interface PrimaryNavigationProps {
  onNavigate?: () => void
}

export function PrimaryNavigation({ onNavigate }: PrimaryNavigationProps) {
  return (
    <nav aria-label="Primary navigation">
      <ul className="primary-navigation-list">
        {NAVIGATION_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `primary-navigation-link${isActive ? ' primary-navigation-link--active' : ''}`
              }
              onClick={onNavigate}
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
