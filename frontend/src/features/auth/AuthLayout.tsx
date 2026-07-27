import { Link, Outlet } from 'react-router-dom'
import { BrandMark } from '../../components/ui/BrandMark'

export function AuthLayout() {
  return (
    <div className="auth-page">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="auth-header">
        <Link to="/login" aria-label="AI Exam Quality Platform sign in">
          <BrandMark />
        </Link>
      </header>
      <main className="auth-main" id="main-content">
        <Outlet />
      </main>
    </div>
  )
}
