import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ProcessingStage } from '../../types/api'
import { ProcessingStateBadge } from './ProcessingStateBadge'

const PROCESSING_STATES: ProcessingStage[] = [
  'queued',
  'validating',
  'extracting_exam',
  'extracting_tp153',
  'building_evidence',
  'retrieving_knowledge',
  'applying_rules',
  'generating_report',
  'completed',
  'failed',
]

describe('ProcessingStateBadge', () => {
  it.each(PROCESSING_STATES)('preserves the exact backend label "%s"', (state) => {
    render(<ProcessingStateBadge state={state} />)

    const badge = screen.getByLabelText(`Processing state: ${state}`)
    expect(badge).toHaveTextContent(state)
    expect(badge).toHaveAttribute('data-processing-state', state)
    expect(badge).not.toHaveAttribute('data-academic-status')
  })
})
