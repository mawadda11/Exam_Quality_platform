import { Outlet, useLocation } from 'react-router-dom'
import { DevIdentityBar } from '../DevIdentityBar'
import { BrandMark } from '../ui/BrandMark'
import { MobileNavigation } from './MobileNavigation'
import { PrimaryNavigation } from './PrimaryNavigation'

export function AppShell() {
  const location = useLocation()

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <BrandMark />
        <PrimaryNavigation />
      </aside>

      <header className="app-mobile-header">
        <BrandMark size="small" />
        <MobileNavigation key={location.pathname} />
      </header>

      <main className="app-workspace" id="main-content">
        <DevIdentityBar />
        <div className="app-route-content">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
