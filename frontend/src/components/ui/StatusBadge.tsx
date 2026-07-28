import { useI18n } from '../../i18n/I18nProvider'
import type { AcademicStatus } from '../../types/api'

interface StatusPresentation {
  className: string
  icon: string
}

const STATUS_PRESENTATION: Record<AcademicStatus, StatusPresentation> = {
  Satisfied: { className: 'ui-status-badge--satisfied', icon: '✓' },
  'Partially Satisfied': { className: 'ui-status-badge--partial', icon: '!' },
  'Not Satisfied': { className: 'ui-status-badge--not-satisfied', icon: '×' },
  'Not Verified': { className: 'ui-status-badge--not-verified', icon: '?' },
  'Not Applicable': { className: 'ui-status-badge--not-applicable', icon: '–' },
}

export function StatusBadge({ status }: { status: AcademicStatus }) {
  const { t } = useI18n()
  const presentation = STATUS_PRESENTATION[status]

  return (
    <span
      className={`ui-status-badge ${presentation.className}`}
      data-academic-status={status}
    >
      <span aria-hidden="true">{presentation.icon}</span>
      <span>{t(status)}</span>
    </span>
  )
}
