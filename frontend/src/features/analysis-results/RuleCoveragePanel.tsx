import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import type {
  RuleCoverageAuditResponse,
  RuleRuntimeDisposition,
} from '../../types/api'
import { StatusBadge } from './StatusBadge'
import type { ResultResource } from './useAnalysisResultsData'

const RUNTIME_LABELS: Record<RuleRuntimeDisposition, string> = {
  evaluated: 'Evaluated',
  conditional_capability_gap: 'Conditional capability gap',
  unsupported: 'Unsupported',
  not_run: 'Not run',
}

function CoverageSummary({ coverage }: { coverage: RuleCoverageAuditResponse }) {
  return (
    <>
      <div className="coverage-summary-grid" aria-label="Rule execution coverage summary">
        <div>
          <strong>{coverage.evaluated_rules}</strong>
          <span>Evaluated</span>
        </div>
        <div>
          <strong>{coverage.conditional_capability_gap_rules}</strong>
          <span>Conditional gaps</span>
        </div>
        <div>
          <strong>{coverage.unsupported_rules}</strong>
          <span>Unsupported</span>
        </div>
        <div>
          <strong>{coverage.not_run_rules}</strong>
          <span>Not run</span>
        </div>
      </div>

      <Alert
        variant={coverage.runtime_integrity_ok ? 'success' : 'error'}
        title={
          coverage.runtime_integrity_ok
            ? 'Supported rule execution is complete'
            : 'System execution coverage gap detected'
        }
      >
        {coverage.runtime_integrity_ok
          ? `All supported rules expected for this runtime were accounted for across ${coverage.total_rules} governed exam-facing rules.`
          : 'One or more supported rules did not persist a finding. This is an operational system gap, not an academic Not Verified result.'}
      </Alert>

      <ResponsiveTable caption="Governed rule execution coverage">
        <thead>
          <tr>
            <th>Rule</th>
            <th>Requirement</th>
            <th>Capability</th>
            <th>Runtime result</th>
            <th>Academic result</th>
            <th>Explanation</th>
          </tr>
        </thead>
        <tbody>
          {coverage.entries.map((entry) => (
            <tr key={entry.rule_id}>
              <td>
                <strong>
                  <bdi>{entry.rule_id}</bdi>
                </strong>
                <div className="coverage-cell-note">{entry.rule_name}</div>
              </td>
              <td>
                <bdi>{entry.requirement_id}</bdi>
                <div className="coverage-cell-note">{entry.requirement_name}</div>
              </td>
              <td>
                {entry.support_status.replaceAll('_', ' ')}
                <div className="coverage-cell-note">
                  {entry.evaluation_mode.replaceAll('_', ' ')}
                </div>
              </td>
              <td>
                <span
                  className={`runtime-disposition runtime-disposition--${entry.runtime_disposition}`}
                  data-runtime-disposition={entry.runtime_disposition}
                >
                  {RUNTIME_LABELS[entry.runtime_disposition]}
                </span>
              </td>
              <td>
                {entry.finding_status ? (
                  <StatusBadge status={entry.finding_status} />
                ) : (
                  <span className="coverage-not-academic">Not an academic status</span>
                )}
              </td>
              <td dir="auto">
                {entry.reason ?? 'Executed as designed.'}
                {entry.planned_milestone_or_dependency && (
                  <div className="coverage-cell-note">
                    Dependency: {entry.planned_milestone_or_dependency}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </ResponsiveTable>
    </>
  )
}

interface RuleCoveragePanelProps {
  coverage: ResultResource<RuleCoverageAuditResponse>
  onRetry: () => void
}

export function RuleCoveragePanel({ coverage, onRetry }: RuleCoveragePanelProps) {
  return (
    <Card as="section" className="results-content-card rule-coverage-panel">
      <h3>Rule execution coverage</h3>
      <p>
        Operational coverage is shown separately from academic findings. Unsupported or unexecuted
        capability is never converted into Not Verified.
      </p>

      {coverage.status === 'loading' && (
        <div className="results-resource-state" role="status" aria-busy="true">
          Loading rule execution coverage…
        </div>
      )}
      {coverage.status === 'error' && (
        <Alert variant="error" title="Could not load rule execution coverage">
          <p>{coverage.message}</p>
          <Button variant="secondary" onClick={onRetry}>
            Retry rule coverage
          </Button>
        </Alert>
      )}
      {coverage.status === 'ready' && <CoverageSummary coverage={coverage.data} />}
    </Card>
  )
}
