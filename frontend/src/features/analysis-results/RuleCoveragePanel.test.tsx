import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { RuleCoverageAuditResponse } from '../../types/api'
import { RuleCoveragePanel } from './RuleCoveragePanel'

const COVERAGE: RuleCoverageAuditResponse = {
  analysis_id: 'analysis-1',
  scope: 'exam_facing_rules',
  total_rules: 3,
  evaluated_rules: 1,
  conditional_capability_gap_rules: 0,
  unsupported_rules: 1,
  not_run_rules: 1,
  runtime_integrity_ok: false,
  entries: [
    {
      requirement_id: 'REQ001',
      rule_id: 'RULE001',
      requirement_name: 'Question-to-CLO Mapping',
      rule_name: 'CLO Mapping',
      support_status: 'supported',
      evaluation_mode: 'semantic_or_hybrid',
      design_disposition: 'design_authorized',
      runtime_disposition: 'evaluated',
      finding_status: 'Satisfied',
      evaluator_type: 'semantic_ai',
      implemented_milestone: 'M7',
      reason: null,
      planned_milestone_or_dependency: null,
    },
    {
      requirement_id: 'REQ015',
      rule_id: 'RULE015',
      requirement_name: 'Referenced Material Quality',
      rule_name: 'Referenced Material Quality',
      support_status: 'unsupported',
      evaluation_mode: 'no_authorized_method',
      design_disposition: 'deferred',
      runtime_disposition: 'unsupported',
      finding_status: null,
      evaluator_type: null,
      implemented_milestone: null,
      reason: 'No authorized method exists.',
      planned_milestone_or_dependency: 'Approved referenced-material method',
    },
    {
      requirement_id: 'REQ018',
      rule_id: 'RULE018',
      requirement_name: 'Correct Total Marks',
      rule_name: 'Marks Total',
      support_status: 'supported',
      evaluation_mode: 'deterministic',
      design_disposition: 'design_authorized',
      runtime_disposition: 'not_run',
      finding_status: null,
      evaluator_type: null,
      implemented_milestone: 'M6',
      reason: 'Runtime coverage gap.',
      planned_milestone_or_dependency: null,
    },
  ],
}

describe('RuleCoveragePanel', () => {
  it('keeps operational runtime gaps separate from academic statuses', () => {
    render(
      <RuleCoveragePanel
        coverage={{ status: 'ready', data: COVERAGE }}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getByText(/system execution coverage gap detected/i)).toBeInTheDocument()
    expect(screen.getAllByText('Not run')).toHaveLength(2)
    expect(screen.getAllByText('Not an academic status')).toHaveLength(2)
    expect(screen.getByText('Satisfied')).toBeInTheDocument()
    expect(screen.getByText(/never converted into Not Verified/i)).toBeInTheDocument()
  })

  it('offers a scoped retry when the coverage request fails', () => {
    const onRetry = vi.fn()
    render(
      <RuleCoveragePanel
        coverage={{ status: 'error', message: 'Coverage unavailable.' }}
        onRetry={onRetry}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /retry rule coverage/i }))
    expect(onRetry).toHaveBeenCalledOnce()
  })
})
