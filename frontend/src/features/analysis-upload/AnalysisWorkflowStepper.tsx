import { ProgressStepper, type ProgressStep } from '../../components/ui/ProgressStepper'
import { useI18n } from '../../i18n/I18nProvider'

export type AnalysisWorkflowStep =
  | 'information'
  | 'documents'
  | 'review'
  | 'extraction'
  | 'complete'

const WORKFLOW_STEPS = [
  { id: 'information', label: 'Exam Information' },
  { id: 'documents', label: 'Upload Documents' },
  { id: 'review', label: 'Review and Start' },
  { id: 'extraction', label: 'Review Extraction' },
] as const

interface AnalysisWorkflowStepperProps {
  currentStep: AnalysisWorkflowStep
}

export function AnalysisWorkflowStepper({ currentStep }: AnalysisWorkflowStepperProps) {
  const { t } = useI18n()
  const currentIndex =
    currentStep === 'complete'
      ? WORKFLOW_STEPS.length
      : WORKFLOW_STEPS.findIndex((step) => step.id === currentStep)

  const steps: ProgressStep[] = WORKFLOW_STEPS.map((step, index) => ({
    ...step,
    label: t(step.label),
    status: index < currentIndex ? 'complete' : index === currentIndex ? 'current' : 'upcoming',
  }))

  return <ProgressStepper steps={steps} ariaLabel={t('New analysis progress')} />
}
