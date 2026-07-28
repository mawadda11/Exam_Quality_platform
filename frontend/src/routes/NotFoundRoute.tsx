import { Link } from 'react-router-dom'
import { PageState } from '../components/ui/PageState'
import { useI18n } from '../i18n/I18nProvider'

export function NotFoundRoute() {
  const { t } = useI18n()
  return (
    <div className="route-content-compact">
      <PageState
        state="error"
        title={t('Page not found')}
        message={t('This application route does not exist.')}
        action={
          <Link className="ui-button ui-button--secondary" to="/dashboard">
            {t('Return to dashboard')}
          </Link>
        }
      />
    </div>
  )
}
