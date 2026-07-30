import { Link, Outlet } from 'react-router-dom'
import { BrandMark } from '../../components/ui/BrandMark'
import { LanguageSwitcher } from '../../i18n/LanguageSwitcher'
import { useI18n } from '../../i18n/I18nProvider'

export function AuthLayout() {
  const { t } = useI18n()
  return (
    <div className="auth-page">
      <a className="skip-link" href="#main-content">
        {t('Skip to main content')}
      </a>
      <header className="auth-header">
        <Link to="/login" aria-label={`${t('Exam Quality Analyzer')} ${t('Sign in')}`}>
          <BrandMark />
        </Link>
        <LanguageSwitcher />
      </header>
      <main className="auth-main" id="main-content">
        <Outlet />
      </main>
    </div>
  )
}
