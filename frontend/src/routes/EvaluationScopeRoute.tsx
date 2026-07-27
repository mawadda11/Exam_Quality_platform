import { Card } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import {
  LIMITED_EVALUATION_SCOPE,
  PLANNED_EVALUATION_SCOPE,
  SUPPORTED_EVALUATION_SCOPE,
  type EvaluationScopeItem,
} from '../features/platform-scope/platformScopeData'

function ScopeList({ items }: { items: EvaluationScopeItem[] }) {
  return (
    <ul className="evaluation-scope-list">
      {items.map((item) => (
        <li key={item.ruleId}>
          <div>
            <h3>{item.title}</h3>
            <p>{item.description}</p>
          </div>
          <span className="evaluation-scope-rule-id">{item.ruleId}</span>
        </li>
      ))}
    </ul>
  )
}

export function EvaluationScopeRoute() {
  return (
    <div className="route-stack route-content-wide evaluation-scope-route">
      <PageHeader
        eyebrow="Release v1.0.0"
        title="What the Platform Evaluates"
        description="See which exam-quality checks are available now, which check has a defined limitation, and which checks are planned for a later release. Planned checks are not treated as exam failures and do not reduce the score."
      />

      <div className="evaluation-scope-summary" aria-label="Current evaluation scope summary">
        <Card as="article">
          <strong>{SUPPORTED_EVALUATION_SCOPE.length}</strong>
          <span>Available checks</span>
        </Card>
        <Card as="article">
          <strong>{LIMITED_EVALUATION_SCOPE.length}</strong>
          <span>Check with a defined limitation</span>
        </Card>
        <Card as="article">
          <strong>{PLANNED_EVALUATION_SCOPE.length}</strong>
          <span>Planned checks</span>
        </Card>
      </div>

      <Card as="section" className="evaluation-scope-section">
        <h2>Available in this release</h2>
        <p>
          These checks can produce an academic result when the uploaded exam and TP-153 contain
          sufficient confirmed evidence.
        </p>
        <ScopeList items={SUPPORTED_EVALUATION_SCOPE} />
      </Card>

      <Card as="section" className="evaluation-scope-section evaluation-scope-section--limited">
        <h2>Available with a defined limitation</h2>
        <p>
          This check is supported only for the documented cases below. The system does not invent
          a threshold for cases that require an approved academic method.
        </p>
        <ScopeList items={LIMITED_EVALUATION_SCOPE} />
      </Card>

      <Card as="section" className="evaluation-scope-section evaluation-scope-section--planned">
        <h2>Planned for a future release</h2>
        <p>
          These checks remain documented so the platform does not hide its current boundaries.
          They are not scored and are not shown as failures in an individual exam result.
        </p>
        <ScopeList items={PLANNED_EVALUATION_SCOPE} />
      </Card>

      <Card as="section" className="evaluation-scope-section evaluation-scope-scoring-note">
        <h2>How the displayed score should be read</h2>
        <p>
          The displayed score summarizes only verified, applicable checks completed for the
          uploaded exam. Checks marked Not Verified or Not Applicable remain visible in the result
          but do not lower the score. Planned platform capabilities are also excluded.
        </p>
      </Card>
    </div>
  )
}
