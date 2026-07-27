import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { RuleCoverageAuditResponse } from '../../types/api'
import { RuleCoveragePanel } from './RuleCoveragePanel'

const COVERAGE: RuleCoverageAuditResponse = {
  analysis_id: 'analysis-1',
  scope: 'exam_facing_rules',
  total_rules: 21,
  evaluated_rules: 14,
  conditional_capability_gap_rules: 1,
  unsupported_rules: 6,
  not_run_rules: 0,
  runtime_integrity_ok: true,
  entries: [],
}

function renderPanel(coverage = COVERAGE, onRetry = vi.fn()) {
  return render(
    <MemoryRouter>
      <RuleCoveragePanel coverage={{ status: 'ready', data: coverage }} onRetry={onRetry} />
    </MemoryRouter>,
  )
}

describe('RuleCoveragePanel', () => {
  it('shows only analysis-specific completion information and links to platform scope', () => {
    renderPanel()

    expect(screen.getByText(/analysis completed with a limited check/i)).toBeInTheDocument()
    expect(screen.getByText(/does not count as an exam failure/i)).toBeInTheDocument()
    expect(screen.queryByText('14')).not.toBeInTheDocument()
    expect(screen.queryByText('6')).not.toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /see what the platform evaluates/i }))
      .toHaveAttribute('href', '/evaluation-scope')
  })

  it('surfaces an actual runtime failure as a system issue rather than an academic result', () => {
    renderPanel({ ...COVERAGE, runtime_integrity_ok: false, not_run_rules: 1 })

    expect(screen.getByText(/analysis execution needs attention/i)).toBeInTheDocument()
    expect(screen.getByText(/system execution issue, not an academic result/i))
      .toBeInTheDocument()
  })

  it('offers a scoped retry when the completion check fails', () => {
    const onRetry = vi.fn()
    render(
      <MemoryRouter>
        <RuleCoveragePanel
          coverage={{ status: 'error', message: 'Coverage unavailable.' }}
          onRetry={onRetry}
        />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: /retry completion check/i }))
    expect(onRetry).toHaveBeenCalledOnce()
  })
})
