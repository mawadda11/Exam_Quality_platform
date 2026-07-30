import { NavLink } from 'react-router-dom'
import { useI18n } from '../../i18n/I18nProvider'
import { SidebarIcon, type SidebarIconName } from './SidebarIcon'

const NAVIGATION_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', end: true, icon: 'dashboard' },
  { to: '/analyses', label: 'Analyses', end: true, icon: 'analyses' },
  { to: '/reports', label: 'Reports', end: false, icon: 'reports' },
  {
    to: '/evaluation-scope',
    label: 'Methodology & Help',
    end: true,
    icon: 'methodology',
  },
] as const satisfies ReadonlyArray<{
  to: string
  label: string
  end: boolean
  icon: SidebarIconName
}>

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
              <SidebarIcon name={item.icon} />
              {t(item.label)}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
