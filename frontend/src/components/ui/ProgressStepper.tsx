import type { CSSProperties } from 'react'
import { useI18n } from '../../i18n/I18nProvider'

export type ProgressStepStatus = 'complete' | 'current' | 'upcoming'

export interface ProgressStep {
  id: string
  label: string
  status: ProgressStepStatus
}

interface ProgressStepperProps {
  steps: ProgressStep[]
  ariaLabel?: string
}

export function ProgressStepper({
  steps,
  ariaLabel = 'Progress',
}: ProgressStepperProps) {
  const { t } = useI18n()
  const style = { '--step-count': Math.max(steps.length, 1) } as CSSProperties

  return (
    <ol className="ui-progress-stepper" aria-label={ariaLabel} style={style}>
      {steps.map((step, index) => (
        <li
          key={step.id}
          className={`ui-progress-step ui-progress-step--${step.status}`}
          aria-current={step.status === 'current' ? 'step' : undefined}
          data-step-status={step.status}
        >
          <span className="ui-progress-step-marker" aria-hidden="true">
            {step.status === 'complete' ? '✓' : index + 1}
          </span>
          <span>{step.label}</span>
          {step.status === 'current' && <span className="visually-hidden">{t('Current step')}</span>}
        </li>
      ))}
    </ol>
  )
}
