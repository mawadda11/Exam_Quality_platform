import { NavLink } from 'react-router-dom'
import { useI18n } from '../../i18n/I18nProvider'

const NAVIGATION_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', end: true },
  { to: '/analyses', label: 'Analyses', end: true },
  { to: '/evaluation-scope', label: 'What We Evaluate', end: true },
] as const

interface PrimaryNavigationProps {
  onNavigate?: () => void
}

export function PrimaryNavigation({ onNavigate }: PrimaryNavigationProps) {
  const { t } = useI18n()
  return (
    <nav aria-label={t('Primary navigation')}>
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
              {t(item.label)}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
