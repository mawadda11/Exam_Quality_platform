import { Link } from 'react-router-dom'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import type { RuleCoverageAuditResponse } from '../../types/api'
import type { ResultResource } from './useAnalysisResultsData'

function readyMessage(coverage: RuleCoverageAuditResponse) {
  if (!coverage.runtime_integrity_ok) {
    return {
      variant: 'error' as const,
      title: 'Analysis execution needs attention',
      body: `${coverage.not_run_rules} supported ${coverage.not_run_rules === 1 ? 'check did' : 'checks did'} not complete. This is a system execution issue, not an academic result for the exam.`,
    }
  }

  if (coverage.conditional_capability_gap_rules > 0) {
    return {
      variant: 'warning' as const,
      title: 'Analysis completed with a limited check',
      body: `${coverage.conditional_capability_gap_rules} ${coverage.conditional_capability_gap_rules === 1 ? 'check could' : 'checks could'} not be fully evaluated for this analysis because the platform does not yet have an approved method for that case. This does not count as an exam failure.`,
    }
  }

  return {
    variant: 'success' as const,
    title: 'Analysis completed successfully',
    body: 'All checks supported for this analysis completed successfully.',
  }
}

interface RuleCoveragePanelProps {
  coverage: ResultResource<RuleCoverageAuditResponse>
  onRetry: () => void
}

export function RuleCoveragePanel({ coverage, onRetry }: RuleCoveragePanelProps) {
  return (
    <Card as="section" className="results-content-card rule-coverage-panel">
      <h3>Analysis completion</h3>

      {coverage.status === 'loading' && (
        <div className="results-resource-state" role="status" aria-busy="true">
          Checking analysis completion…
        </div>
      )}
      {coverage.status === 'error' && (
        <Alert variant="error" title="Could not confirm analysis completion">
          <p>{coverage.message}</p>
          <Button variant="secondary" onClick={onRetry}>
            Retry completion check
          </Button>
        </Alert>
      )}
      {coverage.status === 'ready' && (() => {
        const message = readyMessage(coverage.data)
        return (
          <>
            <Alert variant={message.variant} title={message.title}>
              {message.body}
            </Alert>
            <p className="results-supporting-text rule-coverage-scope-link">
              <Link to="/evaluation-scope">See what the platform evaluates</Link>
            </p>
          </>
        )
      })()}
    </Card>
  )
}
