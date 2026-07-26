import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AnalysisWorkflowStepper } from './AnalysisWorkflowStepper'

describe('AnalysisWorkflowStepper', () => {
  it('maps the documents route onto the existing shared stepper contract', () => {
    render(<AnalysisWorkflowStepper currentStep="documents" />)

    expect(screen.getByText('Exam Information').closest('li')).toHaveAttribute(
      'data-step-status',
      'complete',
    )
    expect(screen.getByText('Upload Documents').closest('li')).toHaveAttribute(
      'aria-current',
      'step',
    )
    expect(screen.getByText('Review and Start').closest('li')).toHaveAttribute(
      'data-step-status',
      'upcoming',
    )
    expect(screen.getByText('Review Extraction').closest('li')).toHaveAttribute(
      'data-step-status',
      'upcoming',
    )
  })

  it('marks all presentation steps complete after extraction confirmation', () => {
    render(<AnalysisWorkflowStepper currentStep="complete" />)

    expect(screen.getAllByRole('listitem')).toHaveLength(4)
    for (const item of screen.getAllByRole('listitem')) {
      expect(item).toHaveAttribute('data-step-status', 'complete')
      expect(item).not.toHaveAttribute('aria-current')
    }
  })
})

  it('marks extraction review as the current milestone after machine extraction', () => {
    render(<AnalysisWorkflowStepper currentStep="extraction" />)

    expect(screen.getByText('Review and Start').closest('li')).toHaveAttribute(
      'data-step-status',
      'complete',
    )
    expect(screen.getByText('Review Extraction').closest('li')).toHaveAttribute(
      'aria-current',
      'step',
    )
  })
