import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ProgressStepper, type ProgressStep } from './ProgressStepper'

const STEPS: ProgressStep[] = [
  { id: 'details', label: 'Exam Information', status: 'complete' },
  { id: 'documents', label: 'Upload Documents', status: 'current' },
  { id: 'start', label: 'Review and Start', status: 'upcoming' },
]

describe('ProgressStepper', () => {
  it('exposes complete, current, and upcoming states without relying on color', () => {
    render(<ProgressStepper steps={STEPS} ariaLabel="New analysis progress" />)

    expect(screen.getByRole('list', { name: 'New analysis progress' })).toBeInTheDocument()
    expect(screen.getByText('Exam Information').closest('li')).toHaveAttribute(
      'data-step-status',
      'complete',
    )
    expect(screen.getByText('Upload Documents').closest('li')).toHaveAttribute(
      'aria-current',
      'step',
    )
    expect(screen.getByText('Current step')).toBeInTheDocument()
    expect(screen.getByText('Review and Start').closest('li')).toHaveAttribute(
      'data-step-status',
      'upcoming',
    )
  })
})
