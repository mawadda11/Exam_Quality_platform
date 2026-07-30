import { Link, Outlet, useLocation } from 'react-router-dom'
import { BrandMark } from '../ui/BrandMark'
import { MobileNavigation } from './MobileNavigation'
import { PrimaryNavigation } from './PrimaryNavigation'
import { RouteFocusManager } from './RouteFocusManager'
import { UserAccountPanel } from './UserAccountPanel'
import { LanguageSwitcher } from '../../i18n/LanguageSwitcher'
import { useI18n } from '../../i18n/I18nProvider'
import { SidebarIcon } from './SidebarIcon'

export function AppShell() {
  const { t } = useI18n()
  const location = useLocation()

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        {t('Skip to main content')}
      </a>
      <aside className="app-sidebar">
        <BrandMark />
        <Link className="ui-button app-new-analysis-action" to="/analyses/new">
          <SidebarIcon name="new-analysis" />
          {t('New Analysis')}
        </Link>
        <PrimaryNavigation />
        <LanguageSwitcher />
        <UserAccountPanel />
      </aside>

      <header className="app-mobile-header">
        <BrandMark size="small" />
        <MobileNavigation key={location.pathname} />
      </header>

      <main className="app-workspace" id="main-content" tabIndex={-1}>
        <RouteFocusManager />
        <div className="app-route-content">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
