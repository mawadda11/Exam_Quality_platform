import { useI18n } from '../../i18n/I18nProvider'
import type { ProcessingStage } from '../../types/api'

export function ProcessingStateBadge({ state }: { state: ProcessingStage }) {
  const { t } = useI18n()
  return (
    <span
      className="ui-processing-state-badge"
      data-processing-state={state}
      aria-label={`${t('Processing state')}: ${t(state)}`}
    >
      {t(state)}
    </span>
  )
}
