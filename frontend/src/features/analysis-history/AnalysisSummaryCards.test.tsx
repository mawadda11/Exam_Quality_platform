import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { AnalysisResponse } from '../../types/api'
import { AnalysisSummaryCards } from './AnalysisSummaryCards'
import type { ReportsAvailableState } from './useReportsAvailableCount'

const ANALYSES = [
  {
    state: 'completed',
    predecessor_analysis_id: null,
  },
  {
    state: 'completed',
    predecessor_analysis_id: null,
  },
  {
    state: 'failed',
    predecessor_analysis_id: null,
  },
  {
    state: 'queued',
    predecessor_analysis_id: null,
  },
] as AnalysisResponse[]

const READY_REPORTS: ReportsAvailableState = { status: 'ready', count: 7 }

describe('AnalysisSummaryCards', () => {
  it('renders the approved metrics with no score or academic-status labels', () => {
    render(<AnalysisSummaryCards analyses={ANALYSES} reportsAvailable={READY_REPORTS} />)
    const summary = screen.getByRole('region', { name: 'Analysis summary' })

    const totalCard = within(summary)
      .getByRole('heading', { name: 'Total analyses' })
      .closest('article')
    const completedCard = within(summary)
      .getByRole('heading', { name: 'Completed analyses' })
      .closest('article')
    const attentionCard = within(summary)
      .getByRole('heading', { name: 'Analyses needing attention' })
      .closest('article')
    const reportsCard = within(summary)
      .getByRole('heading', { name: 'Reports available' })
      .closest('article')

    expect(totalCard && within(totalCard).getByText('4')).toBeInTheDocument()
    expect(completedCard && within(completedCard).getByText('2')).toBeInTheDocument()
    expect(attentionCard && within(attentionCard).getByText('1')).toBeInTheDocument()
    expect(reportsCard && within(reportsCard).getByText('7')).toBeInTheDocument()

    const cards = summary.querySelectorAll('.analysis-summary-card')
    expect(cards).toHaveLength(4)
    expect(within(summary).queryByText(/score/i)).not.toBeInTheDocument()
    expect(within(summary).queryByText(/satisfied/i)).not.toBeInTheDocument()
  })

  it('shows a loading placeholder for the reports-available count while it loads', () => {
    render(
      <AnalysisSummaryCards analyses={ANALYSES} reportsAvailable={{ status: 'loading' }} />,
    )
    const reportsCard = screen
      .getByRole('heading', { name: 'Reports available' })
      .closest('article')

    expect(reportsCard && within(reportsCard).getByText('—')).toBeInTheDocument()
  })
})
