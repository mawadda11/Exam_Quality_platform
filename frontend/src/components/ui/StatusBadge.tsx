import { useI18n } from '../../i18n/I18nProvider'
import type { AcademicStatus } from '../../types/api'
import { Icon, type IconName } from './Icon'

interface StatusPresentation {
  className: string
  icon: IconName
}

const STATUS_PRESENTATION: Record<AcademicStatus, StatusPresentation> = {
  Satisfied: { className: 'ui-status-badge--satisfied', icon: 'check-circle' },
  'Partially Satisfied': { className: 'ui-status-badge--partial', icon: 'alert-circle' },
  'Not Satisfied': { className: 'ui-status-badge--not-satisfied', icon: 'x-circle' },
  'Not Verified': { className: 'ui-status-badge--not-verified', icon: 'question-circle' },
  'Not Applicable': { className: 'ui-status-badge--not-applicable', icon: 'minus-circle' },
}

export function StatusBadge({ status }: { status: AcademicStatus }) {
  const { t } = useI18n()
  const presentation = STATUS_PRESENTATION[status]

  return (
    <span
      className={`ui-status-badge ${presentation.className}`}
      data-academic-status={status}
    >
      <Icon name={presentation.icon} className="ui-icon--sm" />
      <span>{t(status)}</span>
    </span>
  )
}
