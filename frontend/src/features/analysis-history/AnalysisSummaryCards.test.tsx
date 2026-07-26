import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { AnalysisResponse } from '../../types/api'
import { AnalysisSummaryCards } from './AnalysisSummaryCards'

const ANALYSES = [
  {
    state: 'completed',
    predecessor_analysis_id: null,
  },
  {
    state: 'completed',
    predecessor_analysis_id: 'analysis-1',
  },
  {
    state: 'queued',
    predecessor_analysis_id: null,
  },
] as AnalysisResponse[]

describe('AnalysisSummaryCards', () => {
  it('renders the approved metrics with no score or academic-status labels', () => {
    render(<AnalysisSummaryCards analyses={ANALYSES} />)
    const summary = screen.getByRole('region', { name: 'Analysis summary' })

    expect(within(summary).getByRole('heading', { name: 'Total analyses' }))
      .toBeInTheDocument()
    expect(within(summary).getByRole('heading', { name: 'Completed analyses' }))
      .toBeInTheDocument()
    expect(within(summary).getByRole('heading', { name: 'Linked reanalyses' }))
      .toBeInTheDocument()
    expect(within(summary).getAllByText('3')).toHaveLength(1)
    expect(within(summary).getAllByText('2')).toHaveLength(1)
    expect(within(summary).getAllByText('1')).toHaveLength(1)
    expect(within(summary).queryByText(/score/i)).not.toBeInTheDocument()
    expect(within(summary).queryByText(/satisfied/i)).not.toBeInTheDocument()
  })
})
