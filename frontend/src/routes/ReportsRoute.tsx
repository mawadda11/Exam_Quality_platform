import { Link } from 'react-router-dom'
import { PageHeader } from '../components/ui/PageHeader'
import { ReportsLibrary } from '../features/reports/ReportsLibrary'
import { useI18n } from '../i18n/I18nProvider'

export function ReportsRoute() {
  const { t } = useI18n()
  return (
    <div className="route-stack route-content-wide reports-library-route">
      <PageHeader
        title={t('Reports')}
        description={t(
          'View and download reports generated from your exam analyses.',
        )}
        actions={
          <Link className="reports-context-link" to="/analyses">
            {t('View incomplete analyses')}
          </Link>
        }
      />
      <ReportsLibrary />
    </div>
  )
}
