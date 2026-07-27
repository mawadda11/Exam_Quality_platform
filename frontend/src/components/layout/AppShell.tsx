import { Outlet, useLocation } from 'react-router-dom'
import { BrandMark } from '../ui/BrandMark'
import { MobileNavigation } from './MobileNavigation'
import { PrimaryNavigation } from './PrimaryNavigation'
import { RouteFocusManager } from './RouteFocusManager'
import { UserAccountPanel } from './UserAccountPanel'

export function AppShell() {
  const location = useLocation()

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <aside className="app-sidebar">
        <BrandMark />
        <PrimaryNavigation />
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
