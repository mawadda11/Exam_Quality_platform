import { ProgressStepper, type ProgressStep } from '../../components/ui/ProgressStepper'

export type AnalysisWorkflowStep = 'information' | 'documents' | 'review' | 'complete'

const WORKFLOW_STEPS = [
  { id: 'information', label: 'Exam Information' },
  { id: 'documents', label: 'Upload Documents' },
  { id: 'review', label: 'Review and Start' },
] as const

interface AnalysisWorkflowStepperProps {
  currentStep: AnalysisWorkflowStep
}

export function AnalysisWorkflowStepper({ currentStep }: AnalysisWorkflowStepperProps) {
  const currentIndex =
    currentStep === 'complete'
      ? WORKFLOW_STEPS.length
      : WORKFLOW_STEPS.findIndex((step) => step.id === currentStep)

  const steps: ProgressStep[] = WORKFLOW_STEPS.map((step, index) => ({
    ...step,
    status: index < currentIndex ? 'complete' : index === currentIndex ? 'current' : 'upcoming',
  }))

  return <ProgressStepper steps={steps} ariaLabel="New analysis progress" />
}
